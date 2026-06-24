import numpy as np
import pandas as pd
import joblib
import math
import random

random.seed(42)
np.random.seed(42)

try:
    cosine_sim = joblib.load("ml/cosine_sim.pkl")
    products   = pd.read_csv("ml/products.csv")
except FileNotFoundError:
    print("Run from your project root (D:/PROJECT-MCA/cprp/)")
    exit(1)

categories         = products["main_category"].unique().tolist()
brands_in_products = products.groupby("main_category")["brand"].apply(list).to_dict()

PRICE_TIERS = ["0-50","50-100","100-250","250-500","0-500","500-1k","1k-5k","5k-10k","10k-30k","30k-70k","70k+"]

def price_ok(u, p, tol=1):
    try: return abs(PRICE_TIERS.index(u) - PRICE_TIERS.index(p)) <= tol
    except: return True

same_cat_scores  = []
diff_cat_scores  = []

sample = products.sample(min(300, len(products)), random_state=42)
for _, row in sample.iterrows():
    cat   = str(row["main_category"])
    brand = str(row["brand"])
    idx   = row.name
    scores = cosine_sim[idx]

    for i, score in enumerate(scores):
        p = products.iloc[i]
        if p["main_category"] == cat and p["brand"] == brand:
            continue
        if p["main_category"] == cat:
            same_cat_scores.append(float(score))
        else:
            diff_cat_scores.append(float(score))

same = np.array(same_cat_scores)
diff = np.array(diff_cat_scores)

print("=" * 55)
print("  Score Distribution Analysis")
print("=" * 55)
print(f"\n  Same-category scores (n={len(same):,}):")
print(f"    min    : {same.min():.4f}")
print(f"    p10    : {np.percentile(same, 10):.4f}")
print(f"    p25    : {np.percentile(same, 25):.4f}")
print(f"    median : {np.median(same):.4f}")
print(f"    p75    : {np.percentile(same, 75):.4f}")
print(f"    p90    : {np.percentile(same, 90):.4f}")
print(f"    max    : {same.max():.4f}")

print(f"\n  Different-category scores (n={len(diff):,}):")
print(f"    min    : {diff.min():.4f}")
print(f"    p10    : {np.percentile(diff, 10):.4f}")
print(f"    p25    : {np.percentile(diff, 25):.4f}")
print(f"    median : {np.median(diff):.4f}")
print(f"    p75    : {np.percentile(diff, 75):.4f}")
print(f"    p90    : {np.percentile(diff, 90):.4f}")
print(f"    max    : {diff.max():.4f}")

# Find optimal threshold — maximise F1 on this sample
print(f"\n  Threshold scan (find best F1 separation):")
print(f"  {'Threshold':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Accuracy':>10}")
print(f"  {'-'*52}")

all_scores = np.concatenate([same, diff])
all_labels = np.concatenate([np.ones(len(same)), np.zeros(len(diff))])

for t in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
    preds = (all_scores >= t).astype(int)
    tp = ((preds == 1) & (all_labels == 1)).sum()
    fp = ((preds == 1) & (all_labels == 0)).sum()
    fn = ((preds == 0) & (all_labels == 1)).sum()
    tn = ((preds == 0) & (all_labels == 0)).sum()
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    acc  = (tp + tn) / len(all_labels)
    marker = " ← best" if f1 == max(
        2*(tp2/(tp2+fp2+1e-9))*(tp2/(tp2+fn2+1e-9))/(tp2/(tp2+fp2+1e-9)+tp2/(tp2+fn2+1e-9)+1e-9)
        for t2 in [0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60]
        for tp2,fp2,fn2 in [( ((all_scores>=t2)&(all_labels==1)).sum(), ((all_scores>=t2)&(all_labels==0)).sum(), ((all_scores<t2)&(all_labels==1)).sum() )]
    ) else ""
    print(f"  {t:>10.2f} {prec*100:>9.1f}% {rec*100:>9.1f}% {f1*100:>9.1f}% {acc*100:>9.1f}%{marker}")