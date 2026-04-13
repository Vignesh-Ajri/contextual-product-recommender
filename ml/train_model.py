# ============================================================
# STEP 5 - Train ML Model (Content-Based Filtering)
# File: ml/train_model.py
#
# What this does:
# - Reads cleaned.csv
# - Builds product features using TF-IDF
# - Computes cosine similarity between products
# - Trains K-Means for user segmentation
# - Saves everything as .pkl files
#
# Run ONCE after Day 1 is done.
# Command: python ml/train_model.py
# ============================================================

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
print("  CPRP - ML Model Training")
print("=" * 50)


# ── 1. Load data ──────────────────────────────────────────────
print("\nLoading cleaned data...")
try:
    df = pd.read_csv(CLEAN_FILE)
    print(f"✅ Loaded {len(df)} rows")
except FileNotFoundError:
    print(f"❌ File not found: {CLEAN_FILE}")
    print("Run data/clean_data.py first!")
    exit(1)


# ── 2. Build product features ─────────────────────────────────
# Each product = one text string combining its 3 attributes
# Example: "electronics samsung 50k-70k"
# TF-IDF converts this text into a number vector

print("\nBuilding product features...")

products = df[["main_category", "brand", "price_range"]].drop_duplicates().reset_index(drop=True)
products["product_id"] = products.index

# Combine columns into one descriptive string per product
products["features"] = (
    products["main_category"] + " " +
    products["brand"]         + " " +
    products["price_range"]
)

print(f"✅ Unique products: {len(products)}")


# ── 3. TF-IDF Vectorizer ──────────────────────────────────────
# TF-IDF = converts text words into numbers
# "electronics samsung 50k-70k" → [0.5, 0.8, 0.3 ...]
# Words that appear rarely (like brand names) get higher scores
# Words that appear everywhere (like "unknown") get lower scores

print("\nTraining TF-IDF vectorizer...")

tfidf = TfidfVectorizer(analyzer="word", ngram_range=(1, 2))
tfidf_matrix = tfidf.fit_transform(products["features"])

print(f"✅ TF-IDF matrix: {tfidf_matrix.shape}")


# ── 4. Cosine Similarity ──────────────────────────────────────
# Cosine similarity = how similar are two products?
# Score: 0 = totally different, 1 = identical
# "electronics samsung" vs "electronics apple" → ~0.7 (similar category)
# "electronics samsung" vs "stationery parker" → ~0.1 (different)

print("\nComputing cosine similarity...")
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
print(f"✅ Similarity matrix: {cosine_sim.shape}")


# ── 5. Test recommendation ────────────────────────────────────
# Quick test to make sure the model works before saving

def get_recommendations(category, brand, price_range, top_n=5):
    """Find top N products similar to the given product."""
    query     = f"{category} {brand} {price_range}"
    query_vec = tfidf.transform([query])
    scores    = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_idx   = scores.argsort()[::-1][1:top_n+1]  # skip index 0 (itself)

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


# ── 6. K-Means user segmentation ─────────────────────────────
# Groups users into 5 clusters based on browsing behaviour
# Cluster 0 = budget shoppers, Cluster 1 = electronics lovers, etc.
# Your report calls this "segmentation" in Chapter 2

print("\nTraining K-Means user segmentation...")

# Build matrix: rows=users, columns=categories, values=view count
user_cat = df.groupby(["user_id", "main_category"]).size().unstack(fill_value=0)

kmeans = None
if len(user_cat) >= N_CLUSTERS:
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    kmeans.fit(user_cat)
    counts = dict(zip(*np.unique(kmeans.labels_, return_counts=True)))
    print(f"✅ K-Means trained — cluster sizes: {counts}")
else:
    print(f"⚠️  Not enough users, skipping K-Means")


# ── 7. Save all models ────────────────────────────────────────
# joblib saves Python objects to disk
# API loads them back without retraining every time

print("\nSaving models to ml/ folder...")

joblib.dump(tfidf,      os.path.join(MODEL_DIR, "tfidf.pkl"))
joblib.dump(cosine_sim, os.path.join(MODEL_DIR, "cosine_sim.pkl"))
products.to_csv(        os.path.join(MODEL_DIR, "products.csv"), index=False)

print("✅ tfidf.pkl      — TF-IDF vectorizer")
print("✅ cosine_sim.pkl — similarity matrix")
print("✅ products.csv   — product lookup table")

if kmeans:
    joblib.dump(kmeans,                   os.path.join(MODEL_DIR, "kmeans.pkl"))
    joblib.dump(list(user_cat.columns),   os.path.join(MODEL_DIR, "kmeans_columns.pkl"))
    print("✅ kmeans.pkl     — user segmentation model")

print("\n── Done ─────────────────────────────")
print("Next step: python api/app.py")