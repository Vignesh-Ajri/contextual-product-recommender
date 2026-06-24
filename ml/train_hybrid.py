# ============================================================
# CPRP — Hybrid Score Blending
# ============================================================

import pandas as pd
import numpy as np
import joblib
import os

print("=" * 55)
print("  CPRP — Hybrid Blending")
print("=" * 55)

# ── 1. Load all three catalog-scoped matrices ─────────────────
print("\nLoading similarity matrices...")

try:
    bm25_sim = joblib.load("ml/bm25_sim.pkl")
    print(f"  BM25 sim       : {bm25_sim.shape}  "
          f"({bm25_sim.nbytes/(1024**2):.0f} MB)  OK")
except FileNotFoundError:
    print("  ml/bm25_sim.pkl not found — run ml/cprp_model.py first"); exit(1)

n = bm25_sim.shape[0]   # catalog size — everything is aligned to this

try:
    als_sim = joblib.load("ml/als_item_sim.pkl")
    print(f"  ALS sim        : {als_sim.shape}  "
          f"({als_sim.nbytes/(1024**2):.0f} MB)  OK")
    has_als = True
except FileNotFoundError:
    print("  ml/als_item_sim.pkl not found — ALS weight = 0.0")
    als_sim = np.zeros((n, n), dtype=np.float32)
    has_als = False

try:
    emb_sim = joblib.load("ml/embedding_sim.pkl")
    print(f"  Embedding sim  : {emb_sim.shape}  "
          f"({emb_sim.nbytes/(1024**2):.0f} MB)  OK")
    has_emb = True
except FileNotFoundError:
    print("  ml/embedding_sim.pkl not found — embedding weight = 0.0")
    emb_sim = np.zeros((n, n), dtype=np.float32)
    has_emb = False

# ── 2. Verify all matrices are the same shape ─────────────────
print("\nVerifying matrix shapes...")
shapes = {"bm25": bm25_sim.shape, "als": als_sim.shape, "embed": emb_sim.shape}
for name, shape in shapes.items():
    status = "OK" if shape == (n, n) else f"X MISMATCH (expected {(n,n)})"
    print(f"  {name:>6} : {shape}  {status}")
    if shape != (n, n):
        # Resize mismatched matrix to (n, n) safely
        m = min(shape[0], n)
        resized = np.zeros((n, n), dtype=np.float32)
        resized[:m, :m] = (als_sim if name == "als" else emb_sim)[:m, :m]
        if name == "als":   als_sim = resized
        if name == "embed": emb_sim = resized
        print(f"         → resized to ({n},{n})")

products = pd.read_csv("ml/products.csv")
print(f"\n  Catalog products : {len(products):,}")
print(f"  Total matrix RAM : ~{(bm25_sim.nbytes + als_sim.nbytes + emb_sim.nbytes)/(1024**2):.0f} MB")

# ── 3. Grid search blend weights ─────────────────────────────
print("\nGrid-searching blend weights...")

def evaluate_hybrid(w_b, w_a, w_e, sample_size=150):
    """
    Build hybrid for given weights, return same-category hit rate.
    Operates in-place to avoid allocating extra matrices.
    """
    # Build blend without creating a named intermediate variable
    hybrid = (w_b * bm25_sim + w_a * als_sim + w_e * emb_sim).astype(np.float32)

    sample = products.sample(min(sample_size, len(products)), random_state=42)
    hits = total = 0
    for _, row in sample.iterrows():
        cat = str(row["main_category"])
        idx = row.name
        scores = hybrid[idx].copy(); scores[idx] = 0.0
        count = 0
        for i in np.argsort(scores)[::-1]:
            p = products.iloc[i]
            if str(p["main_category"]) == cat and str(p["brand"]) == str(row["brand"]):
                continue
            hits  += (1 if str(p["main_category"]) == cat else 0)
            total += 1; count += 1
            if count >= 5: break
    del hybrid   # free memory immediately after each eval
    return hits / total * 100 if total > 0 else 0

# Weight combinations that sum to 1.0
combos = []
for w_b in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    for w_a in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        w_e = round(1.0 - w_b - w_a, 2)
        if 0.05 <= w_e <= 0.80:
            combos.append((w_b, w_a, w_e))

print(f"  Testing {len(combos)} weight combos...")
print(f"  {'BM25':>6} {'ALS':>6} {'Embed':>6} {'HitRate':>10}")
print(f"  {'-'*32}")

best_score, best_w = 0, (0.5, 0.3, 0.2)
for w_b, w_a, w_e in combos:
    score  = evaluate_hybrid(w_b, w_a, w_e)
    marker = "  <-- best" if score > best_score else ""
    if score > best_score:
        best_score = score
        best_w     = (w_b, w_a, w_e)
    print(f"  {w_b:>6.2f} {w_a:>6.2f} {w_e:>6.2f} {score:>9.1f}%{marker}")

w_bm25, w_als, w_embed = best_w
print(f"\n  Best: BM25={w_bm25}  ALS={w_als}  Embed={w_embed}  "
      f"Score={best_score:.1f}%")

# ── 4. Build final hybrid matrix ─────────────────────────────
# ~225 MB result — safe
print(f"\nBuilding final hybrid matrix ({n:,}×{n:,})...")
hybrid_sim = (
    w_bm25  * bm25_sim +
    w_als   * als_sim  +
    w_embed * emb_sim
).astype(np.float32)

# Row-normalise to [0, 1]
row_max = hybrid_sim.max(axis=1, keepdims=True)
row_max[row_max == 0] = 1.0
hybrid_sim /= row_max    # in-place to avoid extra allocation

print(f"  Shape  : {hybrid_sim.shape}")
print(f"  Size   : {hybrid_sim.nbytes/(1024**2):.0f} MB")
print(f"  Range  : {hybrid_sim.min():.4f} – {hybrid_sim.max():.4f}")

# ── 5. Save ───────────────────────────────────────────────────
print("\nSaving hybrid artifacts to ml/...")
os.makedirs("ml", exist_ok=True)

joblib.dump(hybrid_sim, "ml/hybrid_v2_sim.pkl")
joblib.dump({
    "bm25":      w_bm25,
    "als":       w_als,
    "embed":     w_embed,
    "hit_rate":  round(best_score, 2),
    "has_als":   has_als,
    "has_embed": has_emb,
    "n_products": n,
}, "ml/hybrid_weights.pkl")

print(f"  ml/hybrid_v2_sim.pkl   — {n:,}×{n:,} blended matrix  "
      f"({hybrid_sim.nbytes/(1024**2):.0f} MB)")
print(f"  ml/hybrid_weights.pkl  — optimal weights + metadata")

print(f"\n  Hybrid model ready.")
print(f"  Weights : BM25={w_bm25}  ALS={w_als}  Embed={w_embed}")
print(f"  Hit rate: {best_score:.1f}%")
print("\n-- Done -------------------------------------------------")
print("Next: python ml/evaluate_model.py")