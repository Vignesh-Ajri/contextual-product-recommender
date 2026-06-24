# ============================================================
# CPRP — Recommendation Model
# ============================================================

import pandas as pd
import numpy as np
import joblib
import os
import math
import itertools
from rank_bm25 import BM25Okapi
from sklearn.preprocessing import MinMaxScaler

print("=" * 55)
print("  CPRP — Model Training")
print("=" * 55)


# ── 1. Load data ──────────────────────────────────
print("\nLoading data...")
try:
    df = pd.read_csv("data/fmcg_events.csv")
    print(f"  Loaded {len(df):,} rows from data/fmcg_events.csv")
except FileNotFoundError:
    print("  data/fmcg_events.csv not found — please run data generation script first!")
    exit(1)


# ── 2. Taxonomy ───────────────────────────────────────────────
PRODUCT_TAGS = {
    "electronics":  "smartphone mobile device screen display battery fast charging",
    "computers":    "laptop desktop processor ram storage computing performance",
    "accessories":  "wearable smartwatch earbuds wireless bluetooth portable",
    "appliances":   "home kitchen energy saving durable warranty service",
    "stationery":   "writing office school pen pencil paper notebook daily",
    "clothing":     "fashion fabric comfort style wear season trend apparel",
    "footwear":     "shoes comfort sole casual sport running walking outdoor",
    "sports":       "fitness outdoor activity performance training exercise",
    "toys":         "play kids children gift fun educational activity",
    "beauty":       "skincare cosmetics personal care hygiene grooming",
    "health":       "wellness supplement medicine fitness nutrition care",
    "grocery":      "food daily essential fresh consume perishable household",
    "books":        "education knowledge learning reference study reading",
    "automotive":   "vehicle car maintenance travel transport accessory",
    "furniture":    "home decor comfort durable long lasting interior",
    "garden":       "outdoor plant nature landscape home maintenance",
    "pet":          "animal companion care feed accessories vet",
    "music":        "audio instrument entertainment creative hobby",
    "gaming":       "console video game entertainment immersive interactive",
}

LIFECYCLE_TIER = {
    "electronics": "longterm", "computers": "longterm",
    "furniture":   "longterm", "automotive": "longterm", "appliances": "longterm",
    "clothing":    "seasonal", "footwear":   "seasonal",
    "accessories": "seasonal", "sports":     "seasonal",
    "beauty":      "mediumterm", "health":   "mediumterm", "books":    "mediumterm",
    "gaming":      "mediumterm", "toys":     "mediumterm", "music":    "mediumterm",
    "garden":      "mediumterm", "pet":      "mediumterm",
    "stationery":  "shortterm",  "grocery":  "shortterm",
}

PRICE_TIER_ORDER = [
    "0-50", "50-100", "100-250", "250-500",
    "0-500", "500-1k", "1k-5k", "5k-10k",
    "10k-30k", "30k-70k", "70k+"
]

LIFECYCLE_SUPPRESSION_DAYS = {
    "longterm": 1095, "seasonal": 365,
    "mediumterm": 180, "shortterm": 7,
}

# Per-category half-life for time decay
CATEGORY_HALF_LIFE = {
    "grocery":    7,    "stationery": 7,
    "beauty":     21,   "health":     21,   "pet":     21,
    "clothing":   45,   "footwear":   45,   "sports":  45,
    "accessories":60,   "books":      60,   "music":   60,
    "toys":       60,   "gaming":     90,   "garden":  90,
    "computers":  120,  "electronics":120,  "appliances":120,
    "automotive": 120,  "furniture":  180,
}
DEFAULT_HALF_LIFE = 30

# Cross-category fallback graph
# When a user's category has no good recommendations, try these related ones
CATEGORY_FALLBACK = {
    "electronics":  ["computers", "accessories", "gaming"],
    "computers":    ["electronics", "accessories", "gaming"],
    "accessories":  ["electronics", "clothing", "sports"],
    "appliances":   ["electronics", "furniture", "garden"],
    "clothing":     ["footwear", "accessories", "sports"],
    "footwear":     ["clothing", "sports", "accessories"],
    "sports":       ["footwear", "clothing", "health"],
    "beauty":       ["health", "grocery"],
    "health":       ["beauty", "grocery", "sports"],
    "grocery":      ["health", "beauty"],
    "books":        ["music", "gaming", "toys"],
    "gaming":       ["electronics", "computers", "books"],
    "toys":         ["books", "gaming", "sports"],
    "music":        ["books", "electronics", "accessories"],
    "furniture":    ["appliances", "garden"],
    "garden":       ["furniture", "pet", "sports"],
    "pet":          ["health", "grocery", "toys"],
    "automotive":   ["electronics", "accessories"],
    "stationery":   ["books", "computers"],
}


# ── 3. Build product catalog ──────────────────────────────────
print("\nBuilding product catalog...")

products = (
    df[["main_category", "brand", "price_range"]]
    .drop_duplicates()
    .reset_index(drop=True)
)
products["product_id"] = products.index


def build_features(row, cat_weight=3, brand_weight=2):
    """Build weighted feature string. Weights tunable for grid search."""
    cat   = str(row["main_category"]).lower()
    brand = str(row["brand"]).lower()
    price = str(row["price_range"]).lower()
    tags  = PRODUCT_TAGS.get(cat, "general product item")
    tier  = LIFECYCLE_TIER.get(cat, "mediumterm")
    return (
        f"{cat} " * cat_weight +
        f"{brand} " * brand_weight +
        f"{price} {tier} {tags}"
    )


# ── 4. Grid search for best field weights ──────────────
print("\nRunning field-weight grid search...")
print("  (Testing category × brand multiplier combinations)")

def evaluate_weights(cat_w, brand_w, products_df, sample_size=150):
    """
    Quick evaluation: build BM25 matrix with given weights,
    return same-category hit rate on a sample.
    """
    feats = products_df.apply(
        lambda r: build_features(r, cat_w, brand_w), axis=1
    )
    tokenized = [f.split() for f in feats]
    bm25 = BM25Okapi(tokenized)

    sample = products_df.sample(min(sample_size, len(products_df)), random_state=42)
    hits = 0
    total = 0

    for _, row in sample.iterrows():
        cat = str(row["main_category"])
        query = build_features(row, cat_w, brand_w).split()
        scores = bm25.get_scores(query)

        # Top 5 excluding self
        ranked = np.argsort(scores)[::-1]
        count = 0
        for i in ranked:
            p = products_df.iloc[i]
            if str(p["main_category"]) == cat and str(p["brand"]) == str(row["brand"]):
                continue
            hits += (1 if str(p["main_category"]) == cat else 0)
            total += 1
            count += 1
            if count >= 5:
                break

    return hits / total * 100 if total > 0 else 0

# Grid search over category and brand weight multipliers
cat_options   = [3, 4, 5, 6, 7, 8, 9, 10]
brand_options = [1, 2, 3, 4, 5]

best_score  = 0
best_cat_w  = 3
best_brand_w= 2

print(f"  {'cat_w':>6} {'brand_w':>8} {'hit_rate':>10}")
print(f"  {'-'*28}")

for cat_w, brand_w in itertools.product(cat_options, brand_options):
    score = evaluate_weights(cat_w, brand_w, products)
    marker = ""
    if score > best_score:
        best_score   = score
        best_cat_w   = cat_w
        best_brand_w = brand_w
        marker = " <-- best"
    print(f"  {cat_w:>6} {brand_w:>8} {score:>9.1f}%{marker}")

print(f"\n  Best weights — category: {best_cat_w}×  brand: {best_brand_w}×  hit rate: {best_score:.1f}%")


# ── 5. Build BM25 matrix with best weights ─────────────
print("\nBuilding BM25 similarity matrix...")

products["features"] = products.apply(
    lambda r: build_features(r, best_cat_w, best_brand_w), axis=1
)

tokenized_corpus = [f.split() for f in products["features"]]
bm25 = BM25Okapi(tokenized_corpus)

print(f"  BM25 corpus size : {len(tokenized_corpus):,} documents")

# Convert BM25 scores to a similarity matrix (normalised to [0, 1])
print("  Computing BM25 similarity matrix (this may take a minute)...")
n = len(products)
bm25_matrix = np.zeros((n, n), dtype=np.float32)

for i in range(n):
    query  = tokenized_corpus[i]
    scores = bm25.get_scores(query)
    bm25_matrix[i] = scores

# Normalise each row to [0, 1] so scores are comparable across queries
row_max = bm25_matrix.max(axis=1, keepdims=True)
row_max[row_max == 0] = 1          # avoid divide-by-zero
bm25_sim = bm25_matrix / row_max

print(f"  BM25 similarity matrix shape : {bm25_sim.shape}")
print(f"  Score range : {bm25_sim.min():.4f} – {bm25_sim.max():.4f}")


# ── 6. Quick accuracy test ────────────────────────────────────
print("\nRunning accuracy test...")

def price_ok(u, p, tol=1):
    try:
        return abs(PRICE_TIER_ORDER.index(u) - PRICE_TIER_ORDER.index(p)) <= tol
    except ValueError:
        return True

def diversify_results(results, max_per_brand=2):
    seen = {}
    out  = []
    for r in results:
        c = seen.get(r["brand"], 0)
        if c < max_per_brand:
            out.append(r)
            seen[r["brand"]] = c + 1
    return out

def get_top_recs(category, brand, price_range, top_n=5):
    match = products[
        (products["main_category"] == category) &
        (products["brand"] == brand)
    ]
    if len(match) == 0:
        match = products[products["main_category"] == category]
    if len(match) == 0:
        return []

    idx    = match.index[0]
    scores = bm25_sim[idx].copy()

    raw  = []
    seen = set()
    for i in np.argsort(scores)[::-1]:
        p  = products.iloc[i]
        pc = str(p["main_category"])
        pb = str(p["brand"])
        if pc == category and pb == brand:
            continue
        if (pc, pb) in seen:
            continue
        seen.add((pc, pb))
        raw.append({
            "main_category": pc,
            "brand": pb,
            "price_range": str(p["price_range"]),
            "score": round(float(scores[i]), 4)
        })
        if len(raw) >= top_n * 4:
            break

    # Cross-category fallback if fewer than top_n same-cat results
    same_cat = [r for r in raw if r["main_category"] == category]
    if len(same_cat) < top_n:
        for fallback_cat in CATEGORY_FALLBACK.get(category, []):
            fb_match = products[products["main_category"] == fallback_cat]
            for _, fp in fb_match.iterrows():
                key = (str(fp["main_category"]), str(fp["brand"]))
                if key not in seen:
                    seen.add(key)
                    raw.append({
                        "main_category": str(fp["main_category"]),
                        "brand": str(fp["brand"]),
                        "price_range": str(fp["price_range"]),
                        "score": round(float(bm25_sim[idx][fp.name]) * 0.85, 4)
                    })
            if len(raw) >= top_n * 4:
                break

    return diversify_results(raw)[:top_n]

sample = products.sample(min(200, len(products)), random_state=42)
same_cat_hits  = 0
total_recs     = 0
brands_in_recs = set()

for _, row in sample.iterrows():
    recs = get_top_recs(row["main_category"], row["brand"], row["price_range"])
    for r in recs:
        if r["main_category"] == row["main_category"]:
            same_cat_hits += 1
        brands_in_recs.add(r["brand"])
        total_recs += 1

hit_rate       = same_cat_hits / total_recs * 100 if total_recs > 0 else 0
brand_coverage = len(brands_in_recs) / products["brand"].nunique() * 100

print(f"  Same-category hit rate : {hit_rate:.1f}%")
print(f"  Brand coverage         : {brand_coverage:.1f}%")


# ── 7. Save artifacts ─────────────────────────────────────────
print("\nSaving model artifacts to ml/...")
os.makedirs("ml", exist_ok=True)

joblib.dump(bm25,          "ml/bm25.pkl")
joblib.dump(bm25_sim,      "ml/bm25_sim.pkl")
products.to_csv(           "ml/products.csv", index=False)

joblib.dump(PRODUCT_TAGS,               "ml/product_tags.pkl")
joblib.dump(LIFECYCLE_TIER,             "ml/lifecycle_tier.pkl")
joblib.dump(PRICE_TIER_ORDER,           "ml/price_tier_order.pkl")
joblib.dump(LIFECYCLE_SUPPRESSION_DAYS, "ml/lifecycle_suppression_days.pkl")
joblib.dump(CATEGORY_HALF_LIFE,         "ml/category_half_life.pkl")
joblib.dump(CATEGORY_FALLBACK,          "ml/category_fallback.pkl")
joblib.dump({"cat_weight": best_cat_w, "brand_weight": best_brand_w,
             "hit_rate": round(best_score, 2)}, "ml/best_weights.pkl")

print("  ml/bm25.pkl                  — BM25 model")
print("  ml/bm25_sim.pkl              — BM25 similarity matrix")
print("  ml/best_weights.pkl          — optimal field weights")
print("  ml/category_half_life.pkl    — per-category decay")
print("  ml/category_fallback.pkl     — cross-category graph")
print("  ml/products.csv              — product catalog")
print("  ml/product_tags.pkl          — category semantic tags")
print("  ml/lifecycle_tier.pkl        — lifecycle tiers")
print("  ml/price_tier_order.pkl      — price tier ordering")
print("  ml/lifecycle_suppression_days.pkl — suppression windows")

print(f"\n  Training complete.")
print(f"  Same-category accuracy : {hit_rate:.1f}%")
print(f"  Brand coverage         : {brand_coverage:.1f}%")
print(f"  Best weights           : category={best_cat_w}×  brand={best_brand_w}×")
print("\n-- Done -------------------------------------------------")
print("Next: python ml/evaluate_model.py")