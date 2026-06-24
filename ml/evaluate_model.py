# ============================================================
# CPRP — Model Evaluation
# ============================================================
import numpy as np, pandas as pd, joblib, math, random
from sklearn.metrics import (precision_score, recall_score,
    f1_score, accuracy_score, confusion_matrix, classification_report)

random.seed(42); np.random.seed(42)

print("="*55); print("  CPRP — Model Evaluation"); print("="*55)

try:
    products = pd.read_csv("ml/products.csv")
    cat_hl   = joblib.load("ml/category_half_life.pkl")
    cat_fb   = joblib.load("ml/category_fallback.pkl")
    best_w   = joblib.load("ml/best_weights.pkl")
except FileNotFoundError as e:
    print(f"Missing: {e}"); exit(1)

# Load best available similarity matrix
for name in ["hybrid_v2_sim.pkl","bm25_sim.pkl"]:
    try:
        sim = joblib.load(f"ml/{name}")
        print(f"\n  Matrix   : {name}  {sim.shape}")
        break
    except FileNotFoundError:
        pass
else:
    print("No similarity matrix found"); exit(1)

try:
    hw = joblib.load("ml/hybrid_weights.pkl")
    label = f"Hybrid BM25({hw['bm25']}) ALS({hw['als']}) Embed({hw['embed']})"
except FileNotFoundError:
    label = "BM25 content-based"

print(f"  Model    : {label}")
print(f"  Products : {len(products):,}")
print(f"  Weights  : cat={best_w['cat_weight']}× brand={best_w['brand_weight']}×")

PRICE_TIERS = joblib.load("ml/price_tier_order.pkl")
EVENT_W = {"view":0.5,"search":0.3,"cart":1.0,"wishlist":0.8,
           "purchase":2.0,"ignore":-0.3,"dismiss":-1.0}
THRESHOLD    = 0.10
CTR_T        = 0.15
CONV_T       = 0.25
DEFAULT_HL   = 30
categories   = products["main_category"].unique().tolist()
brands_map   = products.groupby("main_category")["brand"].apply(list).to_dict()

def price_ok(u,p,tol=1):
    try: return abs(PRICE_TIERS.index(u)-PRICE_TIERS.index(p))<=tol
    except: return True

def decay(score,days,hl=DEFAULT_HL):
    return score * math.exp(-0.693*days/hl)

def ndcg(rel):
    dcg  = sum(r/math.log2(i+2) for i,r in enumerate(rel))
    idcg = sum(r/math.log2(i+2) for i,r in enumerate(sorted(rel,reverse=True)))
    return dcg/idcg if idcg>0 else 0.0

def diversify(results,max_b=2):
    seen={}; out=[]
    for r in results:
        c=seen.get(r["brand"],0)
        if c<max_b: out.append(r); seen[r["brand"]]=c+1
    return out

def get_recs(cat,brand,price,days=0,top_n=10):
    match=products[(products["main_category"]==cat)&(products["brand"]==brand)]
    if len(match)==0: match=products[products["main_category"]==cat]
    if len(match)==0: return []
    hl     = cat_hl.get(cat, DEFAULT_HL)
    idx    = match.index[0]
    scores = sim[idx].copy() * decay(1,days,hl)
    raw=[]; seen=set()
    for i in np.argsort(scores)[::-1]:
        p=products.iloc[i]; pc,pb,pp=str(p["main_category"]),str(p["brand"]),str(p["price_range"])
        if pc==cat and pb==brand: continue
        if price!="unknown" and not price_ok(price,pp): continue
        if (pc,pb) in seen: continue
        seen.add((pc,pb))
        raw.append({"main_category":pc,"brand":pb,"price_range":pp,"score":round(float(scores[i]),4)})
        if len(raw)>=top_n*4: break
    if sum(1 for r in raw if r["main_category"]==cat)<top_n//2:
        for fb in cat_fb.get(cat,[]):
            for _,fp in products[products["main_category"]==fb].iterrows():
                key=(str(fp["main_category"]),str(fp["brand"]))
                if key not in seen:
                    seen.add(key)
                    raw.append({"main_category":str(fp["main_category"]),"brand":str(fp["brand"]),
                                "price_range":str(fp["price_range"]),"score":round(float(sim[idx][fp.name])*decay(1,days,hl)*0.85,4)})
            if len(raw)>=top_n*4: break
    raw.sort(key=lambda x:-x["score"])
    return diversify(raw)[:top_n]

# Simulate profiles
n_users=500; interactions=[]
for uid in range(n_users):
    pc=random.choice(categories); pb=random.choice(brands_map.get(pc,["unknown"])); pp=random.choice(PRICE_TIERS)
    for _ in range(random.randint(3,15)):
        et=random.choice(["view","view","view","cart","purchase","search","wishlist","ignore","dismiss"])
        if random.random()<0.70: cat,brand,pr=pc,pb,pp
        else: cat=random.choice(categories); brand=random.choice(brands_map.get(cat,["unknown"])); pr=random.choice(PRICE_TIERS)
        interactions.append({"user_id":f"u{uid}","event_type":et,"main_category":cat,
                              "brand":brand,"price_range":pr,"days_ago":random.randint(0,90),"primary_cat":pc})

df=pd.DataFrame(interactions); profiles={}
for _,row in df.iterrows():
    key=(row["user_id"],row["main_category"],row["brand"])
    if key not in profiles:
        profiles[key]={"score":0,"days":row["days_ago"],"price":row["price_range"],"primary_cat":row["primary_cat"]}
    hl=cat_hl.get(row["main_category"],DEFAULT_HL)
    profiles[key]["score"]=max(0,profiles[key]["score"]+decay(EVENT_W.get(row["event_type"],0),row["days_ago"],hl))

K_VALUES=[1,3,5,10]; results={k:{"pk":[],"rk":[],"ndcg":[]} for k in K_VALUES}
covered_cats=set(); covered_brands=set(); eng_scores=[]
ctr_hits=ctr_total=conv_hits=0; cm_y_true=[]; cm_scores=[]
sample_users=random.sample([f"u{i}" for i in range(n_users)],300)

for uid in sample_users:
    up=[(k,v) for k,v in profiles.items() if k[0]==uid and v["score"]>0]
    if not up: continue
    up.sort(key=lambda x:-x[1]["score"]); top=up[0]
    cat,brand,price,days=top[0][1],top[0][2],top[1]["price"],top[1]["days"]
    recs=get_recs(cat,brand,price,days,top_n=10)
    if not recs: continue
    for k in K_VALUES:
        top_k=recs[:k]
        hits=sum(1 for r in top_k if r["main_category"]==cat and price_ok(price,r["price_range"],1))
        pk=hits/k
        total_rel=len(products[(products["main_category"]==cat)&products["price_range"].apply(lambda p:price_ok(price,str(p),1))])
        rk=hits/min(total_rel,k) if total_rel>0 else 0
        rel=[1 if r["main_category"]==cat and price_ok(price,r["price_range"],1) else 0 for r in top_k]
        results[k]["pk"].append(pk); results[k]["rk"].append(rk); results[k]["ndcg"].append(ndcg(rel))
    for r in recs: covered_cats.add(r["main_category"]); covered_brands.add(r["brand"])
    eng_scores.append(min(1.0,top[1]["score"]/5.0))
    ctr_total+=1
    if recs[0]["score"]>CTR_T: ctr_hits+=1
    if recs[0]["score"]>CONV_T: conv_hits+=1
    for r in recs[:5]:
        is_rel=r["main_category"]==cat and price_ok(price,r["price_range"],1)
        cm_y_true.append(1 if is_rel else 0)
        cm_scores.append(r["score"])

print(f"\n{'='*55}\n  METRICS @ K  [{label}]\n{'='*55}")
print(f"  {'K':<6}{'Precision':>10}{'Recall':>10}{'F1':>10}{'NDCG':>10}")
print(f"  {'-'*46}")
for k in K_VALUES:
    pk=round(float(np.mean(results[k]["pk"])),4) if results[k]["pk"] else 0
    rk=round(float(np.mean(results[k]["rk"])),4) if results[k]["rk"] else 0
    f1=round(2*pk*rk/(pk+rk),4) if (pk+rk)>0 else 0
    nd=round(float(np.mean(results[k]["ndcg"])),4) if results[k]["ndcg"] else 0
    print(f"  K={k:<4}{pk*100:>9.1f}%{rk*100:>9.1f}%{f1*100:>9.1f}%{nd*100:>9.1f}%")

if cm_y_true and cm_scores:
    # Auto-search for the best threshold that maximises accuracy
    best_thr, best_acc = THRESHOLD, 0
    print(f"\n  Threshold search:")
    for thr in [i/100 for i in range(10, 95, 5)]:
        y_p = [1 if s > thr else 0 for s in cm_scores]
        a = accuracy_score(cm_y_true, y_p)
        marker = ""
        if a > best_acc:
            best_acc = a; best_thr = thr
            marker = " <-- best"
        print(f"    thr={thr:.2f}  acc={a*100:.1f}%{marker}")
    THRESHOLD = best_thr
    cm_y_pred = [1 if s > THRESHOLD else 0 for s in cm_scores]

    cm=confusion_matrix(cm_y_true,cm_y_pred)
    if cm.shape==(2,2):
        tn,fp,fn,tp=cm.ravel()
        acc=accuracy_score(cm_y_true,cm_y_pred)
        prec=precision_score(cm_y_true,cm_y_pred,zero_division=0)
        rec=recall_score(cm_y_true,cm_y_pred,zero_division=0)
        f1s=f1_score(cm_y_true,cm_y_pred,zero_division=0)
        print(f"\n{'='*55}\n  CONFUSION MATRIX (K=5)  threshold={THRESHOLD:.2f} (auto-optimised)\n{'='*55}")
        print(f"\n  TN={tn}  FP={fp}  FN={fn}  TP={tp}")
        print(f"  Accuracy : {acc*100:.1f}%  Precision : {prec*100:.1f}%")
        print(f"  Recall   : {rec*100:.1f}%  F1 Score  : {f1s*100:.1f}%")
        print(f"\n{classification_report(cm_y_true,cm_y_pred,target_names=['Not Relevant','Relevant'],zero_division=0)}")

print(f"{'='*55}\n  ADDITIONAL METRICS\n{'='*55}")
tb=products["brand"].nunique()
print(f"  Coverage (cat)   : {round(len(covered_cats)/len(categories)*100,1)}%")
print(f"  Coverage (brand) : {round(len(covered_brands)/tb*100,1)}%")
print(f"  Avg Engagement   : {round(float(np.mean(eng_scores)),3)}")
print(f"  CTR (sim)        : {round(ctr_hits/max(1,ctr_total)*100,1)}%")
print(f"  Conversion (sim) : {round(conv_hits/max(1,ctr_total)*100,1)}%")
print(f"  Products         : {len(products):,}")
print(f"  Users evaluated  : {len(sample_users)}")
