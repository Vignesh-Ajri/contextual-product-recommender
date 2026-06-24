"""
CPRP — Direct MySQL Seeder
Reads data/fmcg_events.csv and populates:
  - users
  - identities
  - user_demographics
  - interactions
  - interest_profiles

Run from project root:
    python db/seed_from_csv.py
"""

import csv
import uuid
import mysql.connector
import os
import sys
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv

load_dotenv()

print("=" * 55)
print("  CPRP — Database Seeder (from fmcg_events.csv)")
print("=" * 55)

CSV_FILE = "data/fmcg_events.csv"

if not os.path.exists(CSV_FILE):
    print(f"ERROR: {CSV_FILE} not found!")
    print("Run: python data/generate_fmcg_data.py  first.")
    sys.exit(1)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3307)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "cprp"),
    "database": os.getenv("DB_NAME", "cprp"),
}

SCORE_WEIGHTS = {
    "view":     {"interest": 0.5,  "browse": 0.5,  "engagement": 0.0, "purchase": 0.0},
    "search":   {"interest": 0.3,  "browse": 0.2,  "engagement": 0.3, "purchase": 0.0},
    "cart":     {"interest": 1.0,  "browse": 0.0,  "engagement": 1.0, "purchase": 0.0},
    "click":    {"interest": 0.4,  "browse": 0.0,  "engagement": 0.4, "purchase": 0.0},
    "purchase": {"interest": 2.0,  "browse": 0.0,  "engagement": 0.5, "purchase": 2.0},
    "dismiss":  {"interest": -1.0, "browse": 0.0,  "engagement": 0.0, "purchase": 0.0},
}

PRICE_ESTIMATE = {
    "0-50": 25, "50-100": 75, "100-250": 175, "250-500": 375,
    "500-1000": 750, "1000-2000": 1500, "2000+": 3000,
    "0-500": 250, "500-1k": 750, "1k-5k": 3000,
}

PRODUCT_LIFETIME = {
    "toothpaste": 10, "toothbrush": 15, "mouthwash": 10,
    "shampoo": 15, "conditioner": 15, "hair_oil": 15,
    "face_wash": 10, "moisturizer": 15, "sunscreen": 10,
    "body_lotion": 15, "lip_balm": 10,
    "lipstick": 15, "foundation": 15, "mascara": 15, "compact_powder": 15,
    "soap": 10, "deodorant": 15, "razor": 5, "hand_sanitizer": 10,
    "detergent": 15, "dishwash": 10, "floor_cleaner": 15,
    "tissue_paper": 5, "toilet_cleaner": 15
}

def parse_size_multiplier(product_name):
    if not product_name: return 1.0
    match = re.search(r'(\d+)\s*(ml|g|kg|l)\b', product_name, re.IGNORECASE)
    if not match: return 1.0
    
    val = float(match.group(1))
    unit = match.group(2).lower()
    
    # Base sizes for standard 1.0 multiplier
    # Assuming 100g or 100ml is standard. 50g = 0.5x, 200g = 2x.
    if unit in ['g', 'ml']:
        return max(0.5, val / 100.0) # Cap minimum multiplier at 0.5
    elif unit in ['kg', 'l']:
        return max(1.0, (val * 1000) / 100.0)
    
    return 1.0

print(f"\nConnecting to MySQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("  Connected!")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# ── In-memory maps to avoid repeated DB lookups ────────────────
user_id_to_core = {}   # user_id (e.g. "user_0001") -> core_id UUID
interest_key_map = {}  # (core_id, category, brand) -> profile_id

print("\nLoading CSV...")
rows = []
with open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"  {len(rows):,} events loaded")

# ── PASS 1: Create users + identities ─────────────────────────
print("\nPass 1: Creating users...")
user_ids_seen = set(r["user_id"] for r in rows)
inserted_users = 0

for uid in user_ids_seen:
    if uid in user_id_to_core:
        continue
    core_id = str(uuid.uuid4())
    user_id_to_core[uid] = core_id
    try:
        cursor.execute("INSERT INTO users (core_id) VALUES (%s)", (core_id,))
        cursor.execute(
            "INSERT INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,%s,%s)",
            (core_id, "user_id", uid)
        )
        inserted_users += 1
    except mysql.connector.IntegrityError:
        # Already exists — fetch
        cursor.execute(
            "SELECT core_id FROM identities WHERE identifier_type='user_id' AND identifier_value=%s",
            (uid,)
        )
        r = cursor.fetchone()
        if r:
            user_id_to_core[uid] = r[0]

conn.commit()
print(f"  {inserted_users} users created")

# ── PASS 2: Demographics (one row per user — first event wins) ─
print("\nPass 2: Inserting demographics...")
demo_done = set()
batch_demos = []
for row in rows:
    uid = row["user_id"]
    core_id = user_id_to_core.get(uid)
    if not core_id or core_id in demo_done:
        continue
    demo_done.add(core_id)
    batch_demos.append((
        core_id,
        row.get("age_group") or None,
        row.get("gender") or None,
        row.get("city") or None,
        row.get("state") or None,
        row.get("country") or "India",
        row.get("device_type") or None,
        row.get("platform") or None,
    ))

if batch_demos:
    cursor.executemany("""
        INSERT IGNORE INTO user_demographics
            (core_id, age_group, gender, city, state, country, device_type, platform)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, batch_demos)
    conn.commit()
print(f"  {len(batch_demos)} demographic rows inserted")

# ── PASS 3: Interactions (bulk insert in chunks) ───────────────
print("\nPass 3: Inserting interactions...")
CHUNK = 1000
interaction_rows = []
for row in rows:
    uid = row["user_id"]
    core_id = user_id_to_core.get(uid)
    if not core_id:
        continue
    interaction_rows.append((
        core_id,
        row.get("event_type", "view"),
        row.get("main_category", "unknown"),
        row.get("brand", "unknown"),
        row.get("price_range", "unknown"),
        row.get("product_name", "") or None,
        row.get("search_query", "") or None,
        row.get("session_id", "") or None,
        row.get("device_type", "") or None,
        row.get("event_time", datetime.now().isoformat()),
        row.get("source", "synthetic"),
    ))

total_ins = 0
for i in range(0, len(interaction_rows), CHUNK):
    batch = interaction_rows[i:i+CHUNK]
    cursor.executemany("""
        INSERT INTO interactions
            (core_id, event_type, main_category, brand, price_range,
             product_name, search_query, session_id, device_type,
             event_time, source)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, batch)
    conn.commit()
    total_ins += len(batch)
    if total_ins % 5000 == 0:
        print(f"  {total_ins:,} interactions inserted...")

print(f"  {total_ins:,} interactions total")

# ── PASS 4: Interest profiles (aggregated) ─────────────────────
print("\nPass 4: Building interest profiles...")

# Aggregate in Python first
from collections import defaultdict as dd

profiles = dd(lambda: {
    "interest_score": 0.0, "browse_score": 0.0,
    "purchase_score": 0.0, "engagement_score": 0.0,
    "browse_count": 0, "cart_count": 0,
    "purchase_count": 0, "dismiss_count": 0,
    "total_spent": 0.0, "last_purchased": None,
    "suppress_until": None, "price_range": "unknown",
})

for row in rows:
    uid    = row["user_id"]
    core_id = user_id_to_core.get(uid)
    if not core_id:
        continue
    cat   = row.get("main_category", "unknown")
    brand = row.get("brand", "unknown")
    price = row.get("price_range", "unknown")
    etype = row.get("event_type", "view").lower()
    etime = row.get("event_time", "")

    key = (core_id, cat, brand)
    p   = profiles[key]
    w   = SCORE_WEIGHTS.get(etype, SCORE_WEIGHTS["view"])

    p["price_range"] = price
    p["interest_score"]    = max(0, p["interest_score"]    + w["interest"])
    p["browse_score"]      = max(0, p["browse_score"]      + w["browse"])
    p["purchase_score"]    = max(0, p["purchase_score"]    + w["purchase"])
    p["engagement_score"]  = max(0, p["engagement_score"]  + w["engagement"])

    if etype == "view":     p["browse_count"]   += 1
    if etype == "cart":     p["cart_count"]     += 1
    if etype == "dismiss":  p["dismiss_count"]  += 1
    if etype == "purchase":
        p["purchase_count"] += 1
        p["total_spent"] += PRICE_ESTIMATE.get(price, 100)
        p["last_purchased"] = etime
        base_lifetime = PRODUCT_LIFETIME.get(cat, 15)
        prod_name = row.get("product_name", "")
        multiplier = parse_size_multiplier(prod_name)
        lifetime = int(base_lifetime * multiplier)
        
        try:
            dt = datetime.fromisoformat(etime)
        except Exception:
            dt = datetime.now()
        p["suppress_until"] = dt + timedelta(days=lifetime)
    if etype == "dismiss":
        try:
            dt = datetime.fromisoformat(etime)
        except Exception:
            dt = datetime.now()
        p["suppress_until"] = dt + timedelta(days=7)

# Bulk insert profiles
profile_rows = []
for (core_id, cat, brand), p in profiles.items():
    profile_rows.append((
        core_id, cat, brand, p["price_range"],
        p["interest_score"], p["browse_score"],
        p["purchase_score"], p["engagement_score"],
        p["browse_count"], p["cart_count"],
        p["purchase_count"], p["dismiss_count"],
        p["total_spent"],
        p["last_purchased"],
        p["suppress_until"],
    ))

for i in range(0, len(profile_rows), CHUNK):
    batch = profile_rows[i:i+CHUNK]
    cursor.executemany("""
        INSERT INTO interest_profiles
            (core_id, main_category, brand, price_range,
             interest_score, browse_score, purchase_score, engagement_score,
             browse_count, cart_count, purchase_count, dismiss_count,
             total_spent, last_purchased, suppress_until)
        VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s)
        ON DUPLICATE KEY UPDATE
            interest_score   = VALUES(interest_score),
            browse_score     = VALUES(browse_score),
            purchase_score   = VALUES(purchase_score),
            engagement_score = VALUES(engagement_score),
            browse_count     = VALUES(browse_count),
            cart_count       = VALUES(cart_count),
            purchase_count   = VALUES(purchase_count),
            dismiss_count    = VALUES(dismiss_count),
            total_spent      = VALUES(total_spent),
            last_purchased   = VALUES(last_purchased),
            suppress_until   = VALUES(suppress_until),
            updated_at       = NOW()
    """, batch)
    conn.commit()

print(f"  {len(profile_rows):,} interest profiles inserted")

# ── Final counts ───────────────────────────────────────────────
cursor.execute("SELECT COUNT(*) FROM users")
u = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM interactions")
i = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM interest_profiles")
ip = cursor.fetchone()[0]

print(f"\n-- Seed Complete ------------------------------------")
print(f"  users             : {u:,}")
print(f"  interactions      : {i:,}")
print(f"  interest_profiles : {ip:,}")
print(f"\nNext steps:")
print(f"  1. python kafka/consumer.py    (in a separate terminal)")
print(f"  2. python api/app.py           (in another terminal)")
print(f"  3. Open dashboard.html")

cursor.close()
conn.close()
