import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

print("=" * 55)
print("  CPRP — Model Evaluation Report")
print("=" * 55)


print("\nLoading models and data...")

try:
    df            = pd.read_csv("data/cleaned.csv")
    tfidf         = joblib.load("ml/tfidf.pkl")
    cosine_sim    = joblib.load("ml/cosine_sim.pkl")
    collab_data   = joblib.load("ml/collab.pkl")
    products_df   = pd.read_csv("ml/products.csv")
    print(f"Loaded {len(df)} rows, {len(products_df)} products")
except FileNotFoundError as e:
    print(f"Missing file: {e}")
    print("Run ml/hybrid_model.py first!")
    exit(1)


print("\n── 1. Content-Based Filtering Evaluation ────────────")

def get_recommendations(category, brand, top_n=5):
    """Get top N similar products for a given category+brand."""
    match = products_df[
        (products_df["main_category"] == category) &
        (products_df["brand"] == brand)
    ]
    if len(match) == 0:
        match = products_df[products_df["main_category"] == category]
    if len(match) == 0:
        return []

    idx = match.index[0]
    scores = list(enumerate(cosine_sim[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = [s for s in scores if s[0] != idx]

    return [products_df.iloc[s[0]]["main_category"] for s in scores[:top_n]]


purchases = df[df["event_type"] == "purchase"].copy()
purchases = purchases.dropna(subset=["main_category", "brand"])
purchases = purchases.head(500)   

hits       = 0
total      = 0
hit_at_3   = 0
hit_at_5   = 0

for _, row in purchases.iterrows():
    recs = get_recommendations(row["main_category"], row["brand"], top_n=5)
    if not recs:
        continue

    total += 1
    if row["main_category"] in recs[:5]:
        hits += 1
        hit_at_5 += 1
    if row["main_category"] in recs[:3]:
        hit_at_3 += 1

precision_at_5 = (hit_at_5 / total * 100) if total > 0 else 0
precision_at_3 = (hit_at_3 / total * 100) if total > 0 else 0

print(f"  Test samples:      {total}")
print(f"  Precision@3:       {precision_at_3:.1f}%")
print(f"  Precision@5:       {precision_at_5:.1f}%")
print(f"  (% of times the purchased category appeared in top K recommendations)")


print(f"\n  Sample similarity scores (Samsung electronics):")
test_match = products_df[
    (products_df["main_category"] == "electronics") &
    (products_df["brand"] == "samsung")
]
if len(test_match) > 0:
    idx = test_match.index[0]
    scores = list(enumerate(cosine_sim[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:6]
    for s in scores:
        p = products_df.iloc[s[0]]
        print(f"    {p['main_category']:15} {p['brand']:12} "
              f"{p['price_range']:10} → similarity: {s[1]:.3f}")


print("\n── 2. Collaborative Filtering Evaluation ────────────")

total_products   = len(products_df)
covered_products = 0

for _, prod in products_df.iterrows():
    item_key = f"{prod['main_category']}_{prod['brand']}"
    if item_key in collab_data["item_keys"]:
        covered_products += 1

coverage = covered_products / total_products * 100
print(f"  Total products in catalog:  {total_products}")
print(f"  Products with collab data:  {covered_products}")
print(f"  Coverage:                   {coverage:.1f}%")
print(f"  (% of products we can give collaborative recommendations for)")

print(f"\n  Sample collab recommendations (electronics_samsung):")
item_key = "electronics_samsung"
if item_key in collab_data["item_keys"]:
    item_idx   = collab_data["item_enc"].transform([item_key])[0]
    raw_collab = collab_data["item_sim_matrix"][item_idx]
    top_items  = np.argsort(raw_collab)[::-1][1:6]
    for i in top_items:
        key   = collab_data["item_keys"][i]
        score = raw_collab[i]
        print(f"    {key:30} → collab score: {score:.3f}")


print("\n── 3. K-Means Clustering Evaluation ─────────────────")

user_cat = df.groupby(
    ["user_id", "main_category"]
).size().unstack(fill_value=0)

user_cat = user_cat[user_cat.sum(axis=1) >= 2]
user_cat = user_cat.head(5000)   
if len(user_cat) >= 5:
    X = user_cat.values

    inertias    = []
    silhouettes = []
    k_range     = range(2, 9)

    print("  Testing K values...")
    for k in k_range:
        km     = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        inertias.append(km.inertia_)
        try:
            sil = silhouette_score(X, labels, sample_size=1000)
            silhouettes.append(sil)
        except:
            silhouettes.append(0)
        print(f"    K={k}: Inertia={km.inertia_:.0f}  Silhouette={silhouettes[-1]:.3f}")

    best_k   = k_range[np.argmax(silhouettes)]
    best_sil = max(silhouettes)
    print(f"\nBest K = {best_k} (Silhouette = {best_sil:.3f})")

    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels   = km_final.fit_predict(X)

    unique, counts = np.unique(labels, return_counts=True)
    print(f"\n  Cluster sizes:")
    for cluster, count in zip(unique, counts):
        print(f"    Cluster {cluster}: {count} users")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor('#0a0e1a')

    ax1.plot(list(k_range), inertias, 'o-', color='#3b82f6', linewidth=2, markersize=6)
    ax1.set_facecolor('#111827')
    ax1.set_title('Elbow Curve — Inertia vs K', color='white', fontsize=12)
    ax1.set_xlabel('Number of Clusters (K)', color='#64748b')
    ax1.set_ylabel('Inertia', color='#64748b')
    ax1.tick_params(colors='#64748b')
    ax1.spines['bottom'].set_color('#1e2d45')
    ax1.spines['left'].set_color('#1e2d45')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(True, color='#1e2d45', linewidth=0.5)

    ax2.plot(list(k_range), silhouettes, 'o-', color='#10b981', linewidth=2, markersize=6)
    ax2.set_facecolor('#111827')
    ax2.set_title('Silhouette Score vs K', color='white', fontsize=12)
    ax2.set_xlabel('Number of Clusters (K)', color='#64748b')
    ax2.set_ylabel('Silhouette Score', color='#64748b')
    ax2.tick_params(colors='#64748b')
    ax2.spines['bottom'].set_color('#1e2d45')
    ax2.spines['left'].set_color('#1e2d45')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.grid(True, color='#1e2d45', linewidth=0.5)
    ax2.axvline(x=best_k, color='#f59e0b', linestyle='--',
                linewidth=1.5, label=f'Best K={best_k}')
    ax2.legend(facecolor='#111827', labelcolor='white')

    plt.tight_layout()
    plt.savefig('ml/kmeans_evaluation.png', dpi=150,
                bbox_inches='tight', facecolor='#0a0e1a')
    print(f"\nElbow + Silhouette plot saved: ml/kmeans_evaluation.png")
else:
    print("Not enough data for clustering evaluation")


print("\n── 4. Hybrid vs Content-Only Comparison ─────────────")

def get_hybrid_recs(category, brand, top_n=5):
    """Get hybrid recommendations."""
    content_scores = np.zeros(len(products_df))
    match = products_df[
        (products_df["main_category"] == category) &
        (products_df["brand"] == brand)
    ]
    if len(match) == 0:
        match = products_df[products_df["main_category"] == category]
    if len(match) > 0:
        idx = match.index[0]
        content_scores = cosine_sim[idx]

    collab_scores = np.zeros(len(products_df))
    item_key = f"{category}_{brand}"
    if item_key in collab_data["item_keys"]:
        item_idx   = collab_data["item_enc"].transform([item_key])[0]
        raw_collab = collab_data["item_sim_matrix"][item_idx]
        for i, prod in products_df.iterrows():
            pk = f"{prod['main_category']}_{prod['brand']}"
            if pk in collab_data["item_keys"]:
                ci = collab_data["item_enc"].transform([pk])[0]
                collab_scores[i] = raw_collab[ci]

    hybrid_scores = 0.5 * content_scores + 0.5 * collab_scores
    result = []
    for i in np.argsort(hybrid_scores)[::-1]:
        prod = products_df.iloc[i]
        if prod["main_category"] == category and prod["brand"] == brand:
            continue
        result.append(prod["main_category"])
        if len(result) >= top_n:
            break
    return result


content_cats = set(get_recommendations("electronics", "samsung", 10))
hybrid_cats  = set(get_hybrid_recs("electronics", "samsung", 10))

print(f"  Content-only unique categories in top 10: {len(content_cats)}")
print(f"  Hybrid unique categories in top 10:       {len(hybrid_cats)}")
print(f"  Hybrid diversity improvement:             "
      f"+{len(hybrid_cats) - len(content_cats)} categories")



print("\n" + "=" * 55)
print("  EVALUATION SUMMARY")
print("=" * 55)
print(f"  Content-Based Precision@5:  {precision_at_5:.1f}%")
print(f"  Content-Based Precision@3:  {precision_at_3:.1f}%")
print(f"  Collaborative Coverage:     {coverage:.1f}%")
if len(user_cat) >= 5:
    print(f"  K-Means Best Silhouette:    {best_sil:.3f}  (K={best_k})")
print(f"  Hybrid Diversity:           {len(hybrid_cats)} unique categories")
print("\n  Files saved:")
print("  ml/kmeans_evaluation.png   — elbow + silhouette plots")
print("=" * 55)