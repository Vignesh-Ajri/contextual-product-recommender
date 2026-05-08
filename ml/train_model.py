import pandas as pd
import joblib
import numpy as np
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

CLEAN_FILE = "data/2019-Oct-cleaned.csv"
MODEL_DIR  = "ml/"
N_CLUSTERS = 5

print("=" * 50)
print("CPRP - ML Model Training")
print("=" * 50)


print("\nLoading cleaned data...")
try:
    df = pd.read_csv(CLEAN_FILE)
    print(f"Loaded {len(df)} rows")
except FileNotFoundError:
    print(f"File not found: {CLEAN_FILE}")
    exit(1)

print("\nBuilding product features...")

products = df[["main_category", "brand", "price_range"]].drop_duplicates().reset_index(drop=True)
products["product_id"] = products.index

products["features"] = (
    products["main_category"] + " " +
    products["brand"]         + " " +
    products["price_range"]
)

print(f"Unique products: {len(products)}")


print("\nTraining TF-IDF vectorizer...")

tfidf = TfidfVectorizer(analyzer="word", ngram_range=(1, 2))
tfidf_matrix = tfidf.fit_transform(products["features"])

print(f" TF-IDF matrix: {tfidf_matrix.shape}")

print("\nComputing cosine similarity...")
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
print(f"Similarity matrix: {cosine_sim.shape}")


def get_recommendations(category, brand, price_range, top_n=5):
    """Find top N products similar to the given product."""
    query     = f"{category} {brand} {price_range}"
    query_vec = tfidf.transform([query])
    scores    = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_idx   = scores.argsort()[::-1][1:top_n+1]

    results = []
    for idx in top_idx:
        results.append({
            "main_category": products.iloc[idx]["main_category"],
            "brand":         products.iloc[idx]["brand"],
            "price_range":   products.iloc[idx]["price_range"],
            "similarity":    round(float(scores[idx]), 3)
        })
    return results

print("\nTesting: 'Samsung electronics 50k-70k'")
for r in get_recommendations("electronics", "samsung", "50k-70k"):
    print(f"  → {r['main_category']} | {r['brand']} | {r['price_range']} | {r['similarity']}")

print("\nTraining K-Means user segmentation...")

user_cat = df.groupby(["user_id", "main_category"]).size().unstack(fill_value=0)

kmeans = None
if len(user_cat) >= N_CLUSTERS:
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    kmeans.fit(user_cat)
    counts = dict(zip(*np.unique(kmeans.labels_, return_counts=True)))
    print(f"K-Means trained — cluster sizes: {counts}")
else:
    print(f"Not enough users, skipping K-Means")


print("\nSaving models to ml/ folder...")

joblib.dump(tfidf,      os.path.join(MODEL_DIR, "tfidf.pkl"))
joblib.dump(cosine_sim, os.path.join(MODEL_DIR, "cosine_sim.pkl"))
products.to_csv(        os.path.join(MODEL_DIR, "products.csv"), index=False)

print("tfidf.pkl — TF-IDF vectorizer")
print("cosine_sim.pkl — similarity matrix")
print("products.csv   — product lookup table")

if kmeans:
    joblib.dump(kmeans, os.path.join(MODEL_DIR, "kmeans.pkl"))
    joblib.dump(list(user_cat.columns), os.path.join(MODEL_DIR, "kmeans_columns.pkl"))
    print("kmeans.pkl     — user segmentation model")

print("\n── Done ────────────")