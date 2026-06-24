# ============================================================
# CPRP — ALS Collaborative Filtering
# ============================================================

import pandas as pd
import numpy as np
import joblib
import os
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares

print("=" * 55)
print("  CPRP — ALS Training")
print("=" * 55)

EVENT_WEIGHTS = {
    "purchase": 4.0, "cart": 2.0, "wishlist": 1.5,
    "view": 1.0, "search": 0.5, "ignore": 0.0, "dismiss": 0.0,
}

# ── 1. Load events ────────────────────────────────────────────
print("\nLoading event data...")
try:
    events = pd.read_csv("data/fmcg_events.csv")
    print(f"  Total events loaded: {len(events):,}")
    
    if "user_id" not in events.columns:
        events["user_id"] = events.get("user_session", "anon_" + events.index.astype(str))
        
    events = events.dropna(subset=["user_id", "main_category", "brand"])
    events = events[["user_id", "event_type", "main_category", "brand"]]
except FileNotFoundError:
    print("  data/fmcg_events.csv not found — cannot train ALS")
    exit(1)

events["weight"] = events["event_type"].map(EVENT_WEIGHTS).fillna(0.0)
events = events[events["weight"] > 0].copy()
print(f"  Total usable events: {len(events):,}")

# ── 2. Load catalog — ALS output matrix restricted to this ────
print("\nLoading catalog products...")
try:
    products = pd.read_csv("ml/products.csv")
    products["product_key"] = (
        products["main_category"].str.lower() + "::" +
        products["brand"].str.lower()
    )
    print(f"  Catalog size: {len(products):,} products")
except FileNotFoundError:
    print("  ml/products.csv not found — run ml/cprp_model.py first"); exit(1)

# ── 3. Build ALL-item index for ALS training ──────────────────
# ALS trains on ALL items seen in events (gives richer factors).
# But we only extract the 7,681 catalog rows for the output matrix.
print("\nBuilding item/user indices for ALS training...")
events["product_key"] = (
    events["main_category"].str.lower() + "::" +
    events["brand"].str.lower()
)

all_keys       = list(set(events["product_key"].unique()))
all_item_index = {k: i for i, k in enumerate(all_keys)}
users          = events["user_id"].unique().tolist()
user_index     = {u: i for i, u in enumerate(users)}

n_items = len(all_keys)
n_users = len(users)
print(f"  ALS training items : {n_items:,}  (full event space)")
print(f"  ALS training users : {n_users:,}")

mem_full_gb = (n_items ** 2 * 4) / (1024 ** 3)
mem_cat_mb  = (len(products) ** 2 * 4) / (1024 ** 2)
print(f"\n  Full N×N matrix would need : {mem_full_gb:.1f} GB  <-- SKIPPED")
print(f"  Catalog-only matrix needs  : {mem_cat_mb:.0f} MB  <-- BUILDING THIS")

# ── 4. Sparse user-item matrix ────────────────────────────────
print("\nBuilding sparse interaction matrix...")
ALPHA = 40.0
rows, cols, data = [], [], []
for _, row in events.iterrows():
    uid = user_index.get(row["user_id"])
    pid = all_item_index.get(row["product_key"])
    if uid is not None and pid is not None:
        rows.append(uid); cols.append(pid); data.append(row["weight"])

user_item = sp.csr_matrix(
    (data, (rows, cols)),
    shape=(n_users, n_items), dtype=np.float32
)
conf = user_item.copy()
conf.data = 1.0 + ALPHA * conf.data
print(f"  Matrix: {user_item.shape}  |  nnz: {user_item.nnz:,}")

# ── 5. Train ALS ──────────────────────────────────────────────
print("\nTraining ALS model (factors=64, iter=20)...")
als = AlternatingLeastSquares(
    factors=64, regularization=0.01, iterations=20,
    alpha=ALPHA, use_gpu=False, random_state=42,
)
als.fit(conf.tocsr(), show_progress=True)
print(f"  Item factors : {als.item_factors.shape}")
print(f"  User factors : {als.user_factors.shape}")

# ── 6. Extract ONLY catalog item factors ──────────────────────
# KEY FIX: gather vectors for 7,681 catalog products only,
# then build a 7,681×7,681 matrix instead of 121k×121k.
print("\nExtracting catalog-only item factors...")
item_factors_all = als.item_factors.astype(np.float32)

# L2-normalise once (cosine sim = dot product after normalisation)
norms = np.linalg.norm(item_factors_all, axis=1, keepdims=True)
norms[norms == 0] = 1.0
item_factors_norm = item_factors_all / norms

n_factors     = item_factors_norm.shape[1]
catalog_vecs  = np.zeros((len(products), n_factors), dtype=np.float32)
covered       = 0

for i, key in enumerate(products["product_key"]):
    idx = all_item_index.get(key)
    if idx is not None:
        catalog_vecs[i] = item_factors_norm[idx]
        covered += 1
    # else: zero vector → no ALS signal for this product

print(f"  Catalog products with ALS signal: {covered:,} / {len(products):,} "
      f"({100*covered/len(products):.1f}%)")

# ── 7. Build catalog-only similarity matrix ───────────────────
# Shape: (7681, 7681) — ~225 MB, safe on any laptop
print(f"\nBuilding catalog similarity matrix ({len(products):,}×{len(products):,})...")
als_item_sim = np.dot(catalog_vecs, catalog_vecs.T).astype(np.float32)
als_item_sim = np.clip(als_item_sim, 0.0, 1.0)
print(f"  Shape : {als_item_sim.shape}")
print(f"  Size  : {als_item_sim.nbytes / (1024**2):.0f} MB")
print(f"  Range : {als_item_sim.min():.4f} – {als_item_sim.max():.4f}")

# ── 8. Quick accuracy check ───────────────────────────────────
import random; random.seed(42)
sample = products.sample(min(100, len(products)), random_state=42)
hits = total = 0
for _, row in sample.iterrows():
    cat = str(row["main_category"])
    idx = row.name
    scores = als_item_sim[idx].copy(); scores[idx] = 0.0
    count = 0
    for i in np.argsort(scores)[::-1]:
        p = products.iloc[i]
        if str(p["main_category"]) == cat and str(p["brand"]) == str(row["brand"]):
            continue
        hits  += (1 if str(p["main_category"]) == cat else 0)
        total += 1; count += 1
        if count >= 5: break
print(f"\n  Same-category hit rate: {hits/total*100:.1f}% in top-5")

# ── 9. Save ───────────────────────────────────────────────────
print("\nSaving artifacts to ml/...")
os.makedirs("ml", exist_ok=True)
joblib.dump(als,              "ml/als_model.pkl")
joblib.dump(als.item_factors, "ml/als_item_factors.pkl")
joblib.dump(als.user_factors, "ml/als_user_factors.pkl")
joblib.dump(all_item_index,   "ml/als_product_index.pkl")
joblib.dump(user_index,       "ml/als_user_index.pkl")
joblib.dump(user_item,        "ml/user_item_matrix.pkl")
joblib.dump(als_item_sim,     "ml/als_item_sim.pkl")   # 7681×7681, safe

print("  ml/als_item_sim.pkl       — catalog similarity  (~225 MB)")
print("  ml/als_model.pkl          — trained ALS model")
print("  ml/als_item_factors.pkl   — full item latent vectors")
print(f"\n  Done. Coverage: {100*covered/len(products):.1f}%")
print("Next: python ml/train_embeddings.py")