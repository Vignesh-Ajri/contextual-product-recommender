# ============================================================
# Hybrid Recommendation Model
# File: ml/hybrid_model.py
#
# What this does:
# Combines TWO approaches:
#
# 1. Content-Based Filtering (what you already have)
#    "Recommend products SIMILAR to what this user likes"
#    Based on: category, brand, price_range features
#
# 2. Collaborative Filtering (NEW)
#    "Recommend products that SIMILAR USERS liked"
#    Based on: users who have same interests bought X → recommend X
#    Like Amazon's "Customers who bought this also bought..."
#
# 3. Hybrid = weighted average of both scores
#    Final score = (0.5 × content score) + (0.5 × collaborative score)
#    You can tune these weights anytime
#
# Why hybrid is better:
# - Content alone: misses products the user hasn't seen yet
# - Collaborative alone: fails for new users (cold start)
# - Hybrid: best of both worlds
#
# Command: python ml/hybrid_model.py
# ============================================================

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder

print("=" * 50)
print("  CPRP — Hybrid Model Training")
print("=" * 50)


# ── 1. Load cleaned data ──────────────────────────────────────
print("\nLoading data...")
try:
    df = pd.read_csv("data/2019-Oct-cleaned.csv")
    print(f"Loaded {len(df)} rows")
except FileNotFoundError:
    print("cleaned.csv not found. Run data/clean_data.py first!")
    exit(1)


# ── 2. Build product catalog (same as before) ─────────────────
print("\nBuilding product catalog...")

products = df.groupby(
    ["main_category", "brand", "price_range"]
).agg(
    total_views    = ("event_type", "count"),
    purchase_count = ("event_type", lambda x: (x == "purchase").sum())
).reset_index()

products["features"] = (
    products["main_category"] + " " +
    products["brand"]         + " " +
    products["price_range"]
)
products["product_id"] = products.index
print(f"{len(products)} unique products")


# ── 3. Content-Based Model (TF-IDF + Cosine) ─────────────────
print("\nTraining Content-Based model...")

tfidf   = TfidfVectorizer(ngram_range=(1,2))
tfidf_matrix = tfidf.fit_transform(products["features"])
content_sim  = cosine_similarity(tfidf_matrix, tfidf_matrix)

print(f"Content similarity matrix: {content_sim.shape}")


# ── 4. Collaborative Filtering (User-Item Matrix) ────────────
print("\nTraining Collaborative Filtering model...")

# Step A: Keep only purchase events (strongest signal)
# We build a matrix: rows = users, columns = product categories
purchases = df[df["event_type"] == "purchase"].copy()

if len(purchases) < 100:
    # Fallback: use all events if too few purchases
    purchases = df.copy()
    print(" Using all events (not enough purchases for pure CF)")

# Step B: Create user-item matrix
# Each row = one user, each column = one product (category+brand combo)
# Value = number of times user interacted with that product

purchases["item_key"] = purchases["main_category"] + "_" + purchases["brand"]

# Encode user_id and item_key as integers (required for matrix)
user_enc = LabelEncoder()
item_enc = LabelEncoder()

purchases["user_idx"] = user_enc.fit_transform(purchases["user_id"].astype(str))
purchases["item_idx"] = item_enc.fit_transform(purchases["item_key"])

n_users = purchases["user_idx"].nunique()
n_items = purchases["item_idx"].nunique()

print(f"  Users: {n_users}, Items: {n_items}")

# Step C: Build sparse user-item matrix
# user_item[i][j] = how many times user i interacted with item j
user_item = np.zeros((n_users, n_items))

for _, row in purchases.iterrows():
    user_item[row["user_idx"]][row["item_idx"]] += 1

# Step D: Compute item-item similarity from user-item matrix
# If user A bought both pen and notebook → pen and notebook are similar
# This is called "item-based collaborative filtering"
item_sim_matrix = cosine_similarity(user_item.T, user_item.T)
# .T = transpose — we want item similarities, not user similarities

print(f"Collaborative similarity matrix: {item_sim_matrix.shape}")

# Save item encoder and matrix for lookup later
collab_data = {
    "item_enc":        item_enc,
    "item_sim_matrix": item_sim_matrix,
    "item_keys":       list(item_enc.classes_)
}


# ── 5. Hybrid scoring function ────────────────────────────────
def get_hybrid_recommendations(category, brand, price_range,
                                top_n=5, weight_content=0.5, weight_collab=0.5):
    """
    Returns top N recommendations using hybrid approach.

    weight_content + weight_collab should = 1.0
    Default: 50% content + 50% collaborative

    Returns list of dicts with product details + hybrid score.
    """

    # ── Content-Based scores ──────────────────────────────────
    content_scores = np.zeros(len(products))

    match = products[
        (products["main_category"] == category) &
        (products["brand"]         == brand)
    ]
    if len(match) == 0:
        match = products[products["main_category"] == category]

    if len(match) > 0:
        idx = match.index[0]
        content_scores = content_sim[idx]

    # ── Collaborative scores ──────────────────────────────────
    collab_scores = np.zeros(len(products))

    item_key = f"{category}_{brand}"
    if item_key in collab_data["item_keys"]:
        item_idx = collab_data["item_enc"].transform([item_key])[0]
        raw_collab = collab_data["item_sim_matrix"][item_idx]

        # Map collab scores back to products catalog
        for i, prod in products.iterrows():
            pk = f"{prod['main_category']}_{prod['brand']}"
            if pk in collab_data["item_keys"]:
                ci = collab_data["item_enc"].transform([pk])[0]
                collab_scores[i] = raw_collab[ci]

    # ── Combine scores ────────────────────────────────────────
    hybrid_scores = (weight_content * content_scores) + \
                    (weight_collab  * collab_scores)

    # Build results
    results = []
    for i in np.argsort(hybrid_scores)[::-1]:
        prod = products.iloc[i]
        # Skip the exact same product
        if prod["main_category"] == category and prod["brand"] == brand:
            continue
        results.append({
            "product_id":    int(prod["product_id"]),
            "main_category": str(prod["main_category"]),
            "brand":         str(prod["brand"]),
            "price_range":   str(prod["price_range"]),
            "content_score": round(float(content_scores[i]), 3),
            "collab_score":  round(float(collab_scores[i]),  3),
            "hybrid_score":  round(float(hybrid_scores[i]),  3)
        })
        if len(results) >= top_n:
            break

    return results


# ── 6. Test it ────────────────────────────────────────────────
print("\n── Test: Samsung electronics ──────────────")
recs = get_hybrid_recommendations("electronics", "samsung", "50k-70k")
for r in recs:
    print(f"  {r['main_category']:15} {r['brand']:12} {r['price_range']:10} "
          f"content={r['content_score']} collab={r['collab_score']} "
          f"hybrid={r['hybrid_score']}")

print("\n── Test: stationery parker ─────────────────")
recs2 = get_hybrid_recommendations("stationery", "parker", "0-500")
for r in recs2:
    print(f"  {r['main_category']:15} {r['brand']:12} {r['price_range']:10} "
          f"hybrid={r['hybrid_score']}")


# ── 7. Save everything ───────────────────────────────────────
print("\nSaving hybrid model...")
os.makedirs("ml", exist_ok=True)

joblib.dump(tfidf,       "ml/tfidf.pkl")
joblib.dump(content_sim, "ml/cosine_sim.pkl")
joblib.dump(collab_data, "ml/collab.pkl")
products.to_csv("ml/products.csv", index=False)

print("ml/tfidf.pkl       — TF-IDF vectorizer")
print("ml/cosine_sim.pkl  — content similarity")
print("ml/collab.pkl      — collaborative model")
print("ml/products.csv    — product catalog")

print("\n── Done ─────────────────────────────────")
print("Next: update api/app.py to use hybrid recommendations")