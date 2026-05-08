import requests
import json

BASE_URL = "http://localhost:5000"
TOKEN    = None


def pretty(response):
    """Print API response in a readable format."""
    print(f"  Status: {response.status_code}")
    try:
        print(f"  Response: {json.dumps(response.json(), indent=4)}")
    except:
        print(f"  Response: {response.text}")
    print()


print("=" * 50)
print("TEST 1: Health Check")
print("=" * 50)
r = requests.get(f"{BASE_URL}/api/health")
pretty(r)


print("=" * 50)
print("TEST 2: Login")
print("=" * 50)
r = requests.post(f"{BASE_URL}/api/login", json={
    "username": "admin",
    "password": "admin123"
})
pretty(r)

if r.status_code == 200:
    TOKEN = r.json().get("token")
    print(f"Got token: {TOKEN[:30]}...")
else:
    print("Login failed — stopping tests")
    exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}


print("=" * 50)
print("TEST 3: Send browse event — Vignesh views Samsung S24")
print("=" * 50)
r = requests.post(f"{BASE_URL}/api/event", headers=HEADERS, json={
    "user_id":      "vignesh_001",
    "event_type":   "view",
    "category":     "electronics",
    "brand":        "samsung",
    "price_range":  "50k-70k",
    "product_name": "Samsung Galaxy S24"
})
pretty(r)


print("=" * 50)
print("TEST 4: Vignesh views Samsung S24 again")
print("=" * 50)
r = requests.post(f"{BASE_URL}/api/event", headers=HEADERS, json={
    "user_id":      "vignesh_001",
    "event_type":   "view",
    "category":     "electronics",
    "brand":        "samsung",
    "price_range":  "50k-70k",
    "product_name": "Samsung Galaxy S24"
})
pretty(r)


# ── Send purchase event ───────────────────────────────
print("=" * 50)
print("TEST 5: Vignesh BUYS Samsung S24 — suppression should trigger")
print("=" * 50)
r = requests.post(f"{BASE_URL}/api/event", headers=HEADERS, json={
    "user_id":      "vignesh_001",
    "event_type":   "purchase",
    "category":     "electronics",
    "brand":        "samsung",
    "price_range":  "50k-70k",
    "product_name": "Samsung Galaxy S24"
})
pretty(r)


print("=" * 50)
print("TEST 6: Get recommendations for Vignesh")
print("(Should be suppressed because he just bought Samsung)")
print("=" * 50)
r = requests.get(f"{BASE_URL}/api/recommend/vignesh_001", headers=HEADERS)
pretty(r)


print("=" * 50)
print("TEST 7: Get full 360 profile for Vignesh")
print("=" * 50)
r = requests.get(f"{BASE_URL}/api/profile/vignesh_001", headers=HEADERS)
pretty(r)


print("=" * 50)
print("TEST 8: Vignesh also buys a Parker pen (stationery)")
print("(Should suppress stationery for 5 days)")
print("=" * 50)
r = requests.post(f"{BASE_URL}/api/event", headers=HEADERS, json={
    "user_id":      "vignesh_001",
    "event_type":   "purchase",
    "category":     "stationery",
    "brand":        "parker",
    "price_range":  "0-500",
    "product_name": "Parker Gel Pen Black"
})
pretty(r)

print("=" * 50)
print("All tests complete!")
print("Check your MySQL tables to verify data was saved:")
print("  SELECT * FROM users;")
print("  SELECT * FROM interest_profiles;")
print("  SELECT * FROM interactions;")
print("=" * 50)