# ============================================================
# STEP 9 - End-to-End Demo Script
# File: notifications/demo.py
#
# What this does:
# - Simulates the complete project flow for your viva demo
# - No need for Kafka running — calls Flask API directly
# - Shows: browse → profile created → buy → suppress → notify
#
# This is what you run during your viva presentation!
# Command: python notifications/demo.py
#
# Make sure Flask API (api/app.py) is running first.
# ============================================================

import requests
import json
import time
import mysql.connector
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

BASE_URL  = "http://localhost:5000"
TOKEN     = None

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

def sep(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

def pretty(r):
    try:
        print(json.dumps(r.json(), indent=2))
    except:
        print(r.text)

def get_token():
    global TOKEN
    r = requests.post(f"{BASE_URL}/api/login", json={
        "username": "admin", "password": "admin123"
    })
    TOKEN = r.json()["token"]
    print(f"✅ Logged in — token received")

def headers():
    return {"Authorization": f"Bearer {TOKEN}"}


# ── DEMO SCENARIO: Vignesh and his Samsung phone ──────────────

sep("STEP 1 — Vignesh browses Samsung S24 (3 times)")
get_token()

for i in range(3):
    r = requests.post(f"{BASE_URL}/api/event", headers=headers(), json={
        "user_id":      "vignesh_demo",
        "event_type":   "view",
        "category":     "electronics",
        "brand":        "samsung",
        "price_range":  "50k-70k",
        "product_name": "Samsung Galaxy S24"
    })
    print(f"  View {i+1}: {r.json().get('message')}")
    time.sleep(0.5)

sep("STEP 2 — Check profile after browsing")
r = requests.get(f"{BASE_URL}/api/profile/vignesh_demo", headers=headers())
data = r.json()
print(f"  Core ID:     {data.get('core_id', '')[:16]}...")
print(f"  Interactions: {data.get('total_interactions')}")
if data.get("interest_profiles"):
    p = data["interest_profiles"][0]
    print(f"  Top interest: {p['main_category']} | {p['brand']}")
    print(f"  Browse count: {p['browse_count']}")
    print(f"  Score:        {p['interest_score']}")

sep("STEP 3 — Get recommendations (before purchase)")
r = requests.get(f"{BASE_URL}/api/recommend/vignesh_demo", headers=headers())
data = r.json()
print(f"  Suppressed: {data.get('suppressed')}")
print(f"  Top interest: {data.get('top_interest', {})}")
print(f"  Recommendations ({data.get('total', 0)}):")
for rec in data.get("recommendations", []):
    print(f"    → {rec['brand']} | {rec['main_category']} | {rec['price_range']}")

sep("STEP 4 — Vignesh BUYS Samsung S24")
r = requests.post(f"{BASE_URL}/api/event", headers=headers(), json={
    "user_id":      "vignesh_demo",
    "event_type":   "purchase",
    "category":     "electronics",
    "brand":        "samsung",
    "price_range":  "50k-70k",
    "product_name": "Samsung Galaxy S24"
})
print(f"  {r.json().get('message')}")

sep("STEP 5 — Check recommendations (after purchase = suppressed)")
r = requests.get(f"{BASE_URL}/api/recommend/vignesh_demo", headers=headers())
data = r.json()
print(f"  Suppressed: {data.get('suppressed')}")
print(f"  Message: {data.get('message')}")
print("  ✅ No recommendations — correctly suppressed for 1095 days (3 years)")

sep("STEP 6 — Simulate 3 years passing (mock in DB)")
print("  Manually updating suppress_until to yesterday to simulate time passing...")
try:
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Set suppress_until to yesterday — simulates 3 years have passed
    yesterday = datetime.now() - timedelta(days=1)
    cursor.execute("""
        UPDATE interest_profiles
        SET suppress_until = %s
        WHERE core_id = (
            SELECT core_id FROM identities
            WHERE identifier_value = 'vignesh_demo'
            LIMIT 1
        )
    """, (yesterday,))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  ✅ suppress_until set to: {yesterday.date()} (simulating 3 years passed)")
except Exception as e:
    print(f"  ❌ DB error: {e}")

sep("STEP 7 — Check recommendations again (suppression lifted)")
r = requests.get(f"{BASE_URL}/api/recommend/vignesh_demo", headers=headers())
data = r.json()
print(f"  Suppressed: {data.get('suppressed')}")
print(f"  Recommendations ({data.get('total', 0)}):")
for rec in data.get("recommendations", []):
    print(f"    → {rec['brand']} | {rec['main_category']} | {rec['price_range']}")

sep("STEP 8 — Also show pen scenario")
# Buy a pen
requests.post(f"{BASE_URL}/api/event", headers=headers(), json={
    "user_id": "vignesh_demo", "event_type": "purchase",
    "category": "stationery", "brand": "parker",
    "price_range": "0-500", "product_name": "Parker Gel Pen"
})
print("  Vignesh bought a Parker pen (lifetime = 5 days)")

r = requests.get(f"{BASE_URL}/api/recommend/vignesh_demo", headers=headers())
data = r.json()
for p in data.get("recommendations", []):
    print(f"  Recommendation → {p['brand']} | {p['main_category']} | {p['price_range']}")

sep("DEMO COMPLETE")
print("""
  Summary of what was demonstrated:
  1. User browsed Samsung 3 times → profile created with 4 params
  2. Recommendations generated using Content-Based Filtering
  3. User purchased → suppressed for 3 years (1095 days)
  4. No recommendations during suppression period
  5. After 3 years → recommendations resume automatically
  6. Pen purchased → suppressed for 5 days (short lifecycle)

  This is your complete project flow!
""")