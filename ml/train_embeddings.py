# ============================================================
# CPRP — Sentence-Transformer Product Embeddings
# ============================================================

import pandas as pd
import numpy as np
import joblib
import os
from sentence_transformers import SentenceTransformer

print("=" * 55)
print("  CPRP — Sentence Embeddings")
print("=" * 55)

# ── 1. Load CATALOG products only ─────────────────────────────
print("\nLoading catalog products...")
try:
    products = pd.read_csv("ml/products.csv")
    print(f"  Catalog size : {len(products):,} products")
    print(f"  (embedding only catalog products — NOT all event items)")
except FileNotFoundError:
    print("  ml/products.csv not found — run ml/cprp_model.py first"); exit(1)

try:
    product_tags = joblib.load("ml/product_tags.pkl")
except FileNotFoundError:
    product_tags = {}
    print("  ml/product_tags.pkl not found — using category name only")

mem_full_gb = (len(products) ** 2 * 4) / (1024 ** 2)
print(f"\n  Similarity matrix will be : {len(products):,}×{len(products):,}")
print(f"  Memory needed             : ~{mem_full_gb:.0f} MB  OK  (safe)")

# ── 2. Build product descriptions ─────────────────────────────
print("\nBuilding product descriptions...")

def build_description(row):
    cat   = str(row["main_category"]).lower()
    brand = str(row["brand"]).lower()
    price = str(row["price_range"]).lower()
    tags  = product_tags.get(cat, "general product")
    return f"{brand} {cat} {price} price range {tags}"

products["description"] = products.apply(build_description, axis=1)
print(f"  Sample: [{products.iloc[0]['main_category']}] "
      f"{products.iloc[0]['description'][:70]}")

# ── 3. Generate embeddings for catalog products only ──────────
print(f"\nLoading sentence-transformer model...")
print("  First run downloads ~90MB — cached after that.")
model = SentenceTransformer("all-MiniLM-L6-v2")

print(f"Encoding {len(products):,} catalog products...")
print("  (CPU encoding, ~30–90 seconds)")

embeddings = model.encode(
    products["description"].tolist(),
    batch_size           = 64,
    show_progress_bar    = True,
    normalize_embeddings = True,   # L2 norm → dot product = cosine
    convert_to_numpy     = True,
)

print(f"\n  Embedding shape : {embeddings.shape}")
print(f"  dtype           : {embeddings.dtype}")
print(f"  Memory used     : {embeddings.nbytes / (1024**2):.0f} MB")

# ── 4. Build catalog-only similarity matrix ───────────────────
# Shape: (7681, 7681) — safe.
# Embeddings are already L2-normalised → dot product = cosine sim.
print(f"\nBuilding embedding similarity matrix ({len(products):,}×{len(products):,})...")

embedding_sim = np.dot(embeddings, embeddings.T).astype(np.float32)
embedding_sim = np.clip(embedding_sim, 0.0, 1.0)

print(f"  Shape  : {embedding_sim.shape}")
print(f"  Size   : {embedding_sim.nbytes / (1024**2):.0f} MB")
print(f"  Range  : {embedding_sim.min():.4f} – {embedding_sim.max():.4f}")

# ── 5. Quick accuracy check ───────────────────────────────────
import random; random.seed(42)
sample = products.sample(min(100, len(products)), random_state=42)
hits = total = 0
for _, row in sample.iterrows():
    cat = str(row["main_category"])
    idx = row.name
    scores = embedding_sim[idx].copy(); scores[idx] = 0.0
    count = 0
    for i in np.argsort(scores)[::-1]:
        p = products.iloc[i]
        if str(p["main_category"]) == cat and str(p["brand"]) == str(row["brand"]):
            continue
        hits  += (1 if str(p["main_category"]) == cat else 0)
        total += 1; count += 1
        if count >= 5: break
print(f"\n  Embedding same-category hit rate: {hits/total*100:.1f}%")

# ── 6. Save ───────────────────────────────────────────────────
print("\nSaving embedding artifacts to ml/...")
os.makedirs("ml", exist_ok=True)
np.save(                   "ml/embeddings.npy",    embeddings)
joblib.dump(embedding_sim, "ml/embedding_sim.pkl")

print(f"  ml/embeddings.npy      — {embeddings.shape[0]:,}×{embeddings.shape[1]} float32")
print(f"  ml/embedding_sim.pkl   — {embedding_sim.shape[0]:,}×{embedding_sim.shape[1]} similarity")
print(f"\n  Done. Hit rate: {hits/total*100:.1f}%")
print("Next: python ml/train_hybrid.py")