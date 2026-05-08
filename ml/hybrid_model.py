import pandas as pd
import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder

print("=" * 50)
print("CPRP — Hybrid Model Training")
print("=" * 50)

print("\nLoading data...")
try:
    df = pd.read_csv("data/2019-Oct-cleaned.csv")
    print(f"Loaded {len(df)} rows")
except FileNotFoundError:
    print("cleaned.csv not found")
    exit(1)

print("\nBuilding product catalog...")

products = df.groupby(
    ["main_category", "brand", "price_range"]
).agg(
    total_views=("event_type", "count"),
    purchase_count=("event_type", lambda x: (x == "purchase").sum())
).reset_index()

products["features"] = (
    products["main_category"] + " " +
    products["brand"] + " " +
    products["price_range"]
)
products["product_id"] = products.index
print(f"{len(products)} unique products")

print("\nTraining Content-Based model...")

tfidf = TfidfVectorizer(ngram_range=(1, 2))
tfidf_matrix = tfidf.fit_transform(products["features"])
content_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

print(f"Content similarity matrix: {content_sim.shape}")

print("\nTraining Collaborative Filtering model...")

purchases = df[df["event_type"] == "purchase"].copy()

if len(purchases) < 100:
    purchases = df.copy()
    print("Using all events (not enough purchases for pure CF)")

purchases["item_key"] = purchases["main_category"] + "_" + purchases["brand"]

user_enc = LabelEncoder()
item_enc = LabelEncoder()

purchases["user_idx"] = user_enc.fit_transform(purchases["user_id"].astype(str))
purchases["item_idx"] = item_enc.fit_transform(purchases["item_key"])

n_users = purchases["user_idx"].nunique()
n_items = purchases["item_idx"].nunique()

print(f"Users: {n_users}, Items: {n_items}")

user_item = np.zeros((n_users, n_items))

for _, row in purchases.iterrows():
    user_item[row["user_idx"]][row["item_idx"]] += 1

item_sim_matrix = cosine_similarity(user_item.T, user_item.T)

print(f"Collaborative similarity matrix: {item_sim_matrix.shape}")

collab_data = {
    "item_enc": item_enc,
    "item_sim_matrix": item_sim_matrix,
    "item_keys": list(item_enc.classes_)
}

def get_hybrid_recommendations(category, brand, price_range,
                               top_n=5, weight_content=0.5, weight_collab=0.5):

    content_scores = np.zeros(len(products))

    match = products[
        (products["main_category"] == category) &
        (products["brand"] == brand)
    ]
    if len(match) == 0:
        match = products[products["main_category"] == category]

    if len(match) > 0:
        idx = match.index[0]
        content_scores = content_sim[idx]

    collab_scores = np.zeros(len(products))

    item_key = f"{category}_{brand}"
    if item_key in collab_data["item_keys"]:
        item_idx = collab_data["item_enc"].transform([item_key])[0]
        raw_collab = collab_data["item_sim_matrix"][item_idx]

        for i, prod in products.iterrows():
            pk = f"{prod['main_category']}_{prod['brand']}"
            if pk in collab_data["item_keys"]:
                ci = collab_data["item_enc"].transform([pk])[0]
                collab_scores[i] = raw_collab[ci]

    hybrid_scores = (weight_content * content_scores) + \
                    (weight_collab * collab_scores)

    results = []
    for i in np.argsort(hybrid_scores)[::-1]:
        prod = products.iloc[i]
        if prod["main_category"] == category and prod["brand"] == brand:
            continue
        results.append({
            "product_id": int(prod["product_id"]),
            "main_category": str(prod["main_category"]),
            "brand": str(prod["brand"]),
            "price_range": str(prod["price_range"]),
            "content_score": round(float(content_scores[i]), 3),
            "collab_score": round(float(collab_scores[i]), 3),
            "hybrid_score": round(float(hybrid_scores[i]), 3)
        })
        if len(results) >= top_n:
            break

    return results

print("\n── Test: Samsung electronics ──────────────")
recs = get_hybrid_recommendations("electronics", "samsung", "50k-70k")
for r in recs:
    print(f"{r['main_category']:15} {r['brand']:12} {r['price_range']:10} "
          f"content={r['content_score']} collab={r['collab_score']} "
          f"hybrid={r['hybrid_score']}")

print("\n── Test: stationery parker ─────────────────")
recs2 = get_hybrid_recommendations("stationery", "parker", "0-500")
for r in recs2:
    print(f"{r['main_category']:15} {r['brand']:12} {r['price_range']:10} "
          f"hybrid={r['hybrid_score']}")

print("\nSaving hybrid model...")
os.makedirs("ml", exist_ok=True)

joblib.dump(tfidf, "ml/tfidf.pkl")
joblib.dump(content_sim, "ml/cosine_sim.pkl")
joblib.dump(collab_data, "ml/collab.pkl")
products.to_csv("ml/products.csv", index=False)

print("ml/tfidf.pkl")
print("ml/cosine_sim.pkl")
print("ml/collab.pkl")
print("ml/products.csv")

print("\n── Done ──")