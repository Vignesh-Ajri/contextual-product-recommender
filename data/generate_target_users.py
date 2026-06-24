import csv
import random
import sys
import uuid
import re
from datetime import datetime, timedelta

OUTPUT_FILE = "data/fmcg_events.csv"

# ── TARGET USERS ──────────────────────────────────────────────
TARGET_EMAILS = [
    "ssvignesh2003@gmail.com",
    "vigneshajri2003@gmail.com",
    "demo03985@gmail.com",
    "vigneshsajri@gmail.com",
    "1ms24mc105@msrit.edu",
    "ssvigga2003@gmail.com"
]

CITIES = [("Bengaluru", "Karnataka"), ("Mumbai", "Maharashtra")]
AGE_GROUPS = ["18-24", "25-34", "35-44"]
GENDERS = ["male", "female"]
DEVICES = ["mobile", "desktop"]
PLATFORMS = ["android", "ios", "web"]

# ── FMCG Product Catalog with Sizes ────────────────────────────
# Weights help determine probability of selection
PRODUCTS = {
    "toothpaste": {"brands": ["colgate", "sensodyne", "pepsodent"], "sizes": ["50g", "100g", "200g", "500g"], "weight": 15},
    "toothbrush": {"brands": ["colgate", "oral-b", "sensodyne"], "sizes": ["1 Pack", "2 Pack", "4 Pack"], "weight": 10},
    "mouthwash": {"brands": ["listerine", "colgate"], "sizes": ["100ml", "250ml", "500ml"], "weight": 5},
    "shampoo": {"brands": ["head-shoulders", "dove", "tresemme", "loreal"], "sizes": ["100ml", "200ml", "500ml", "1L"], "weight": 12},
    "conditioner": {"brands": ["dove", "tresemme", "loreal"], "sizes": ["100ml", "200ml", "500ml"], "weight": 6},
    "hair_oil": {"brands": ["parachute", "dabur", "indulekha"], "sizes": ["50ml", "100ml", "250ml", "500ml"], "weight": 8},
    "hair_color": {"brands": ["garnier", "loreal", "godrej"], "sizes": ["50g", "100g"], "weight": 5},
    "face_wash": {"brands": ["himalaya", "cetaphil", "garnier", "nivea"], "sizes": ["50g", "100g", "200g"], "weight": 10},
    "moisturizer": {"brands": ["nivea", "cetaphil", "vaseline", "pond's"], "sizes": ["50ml", "100ml", "200ml"], "weight": 8},
    "sunscreen": {"brands": ["neutrogena", "lakme", "mamaearth"], "sizes": ["50g", "100g", "200g"], "weight": 7},
    "face_cream": {"brands": ["olay", "pond's", "lakme"], "sizes": ["50g", "100g"], "weight": 6},
    "body_lotion": {"brands": ["nivea", "vaseline", "dove"], "sizes": ["100ml", "200ml", "500ml"], "weight": 6},
    "lip_balm": {"brands": ["nivea", "maybelline", "vaseline"], "sizes": ["5g", "10g"], "weight": 5},
    "lipstick": {"brands": ["maybelline", "lakme", "mac"], "sizes": ["Standard"], "weight": 8},
    "foundation": {"brands": ["maybelline", "lakme", "mac"], "sizes": ["30ml", "50ml"], "weight": 5},
    "mascara": {"brands": ["maybelline", "lakme", "mac"], "sizes": ["Standard"], "weight": 4},
    "eyeliner": {"brands": ["maybelline", "lakme", "colorbar"], "sizes": ["Standard"], "weight": 4},
    "nail_polish": {"brands": ["lakme", "nykaa", "colorbar"], "sizes": ["10ml", "15ml"], "weight": 5},
    "compact_powder": {"brands": ["lakme", "maybelline", "pond's"], "sizes": ["10g", "20g"], "weight": 4},
    "soap": {"brands": ["dove", "lux", "dettol", "pears"], "sizes": ["75g", "100g", "150g", "3 Pack"], "weight": 12},
    "deodorant": {"brands": ["nivea", "dove", "axe", "fogg"], "sizes": ["150ml", "200ml"], "weight": 8},
    "perfume": {"brands": ["wildstone", "engage", "titan"], "sizes": ["50ml", "100ml"], "weight": 5},
    "razor": {"brands": ["gillette", "park-avenue"], "sizes": ["1 Pack", "3 Pack", "5 Pack"], "weight": 5},
    "shaving_cream": {"brands": ["gillette", "park-avenue", "old-spice"], "sizes": ["50g", "100g"], "weight": 5},
    "hand_sanitizer": {"brands": ["dettol", "lifebuoy", "himalaya"], "sizes": ["50ml", "100ml", "500ml"], "weight": 4},
    "detergent": {"brands": ["surf-excel", "ariel", "tide"], "sizes": ["500g", "1kg", "2kg", "5kg"], "weight": 10},
    "dishwash": {"brands": ["vim", "exo", "pril"], "sizes": ["250ml", "500ml", "1L", "500g"], "weight": 6},
    "floor_cleaner": {"brands": ["lizol", "harpic"], "sizes": ["500ml", "1L", "2L"], "weight": 5},
    "tissue_paper": {"brands": ["origami", "paseo"], "sizes": ["1 Pack", "3 Pack"], "weight": 4},
    "toilet_cleaner": {"brands": ["harpic", "domex"], "sizes": ["500ml", "1L"], "weight": 5},
}

EVENT_TYPES = ["view", "view", "view", "cart", "purchase", "search", "click", "dismiss"]

def generate_users():
    users = []
    for email in TARGET_EMAILS:
        city, state = random.choice(CITIES)
        users.append({
            "user_id": email, # Using email directly as the user ID for simplicity in seeding!
            "age_group": random.choice(AGE_GROUPS),
            "gender": random.choice(GENDERS),
            "city": city,
            "state": state,
            "device_type": random.choice(DEVICES),
            "platform": random.choice(PLATFORMS),
            "preferred_categories": random.sample(list(PRODUCTS.keys()), k=random.randint(3, 6))
        })
    return users

def weighted_category_pick():
    categories = list(PRODUCTS.keys())
    weights = [PRODUCTS[c]["weight"] for c in categories]
    return random.choices(categories, weights=weights, k=1)[0]

def determine_price_range(size_str):
    """Estimate a price range based on size to keep it somewhat realistic."""
    num_match = re.search(r'(\d+)', size_str)
    if not num_match: return "100-250"
    val = int(num_match.group(1))
    
    if "kg" in size_str.lower() or "L" in size_str.upper():
        val *= 1000  # Convert to grams/ml for rough sizing
        
    if val < 50: return "0-50"
    if val < 150: return "50-100"
    if val < 300: return "100-250"
    if val < 1000: return "250-500"
    return "500-1000"

def generate_events(users, n_events=1200):
    events = []
    base_time = datetime.now() - timedelta(days=60)

    for i in range(n_events):
        user = random.choice(users)
        category = random.choice(user["preferred_categories"]) if random.random() < 0.7 else weighted_category_pick()
        
        product = PRODUCTS[category]
        brand = random.choice(product["brands"])
        size = random.choice(product["sizes"])
        price_range = determine_price_range(size)
        event_type = random.choice(EVENT_TYPES)
        
        # Recency bias
        days_ago = int(random.triangular(0, 60, 10))
        hours_offset = random.randint(0, 23)
        event_time = base_time + timedelta(days=60 - days_ago, hours=hours_offset)
        
        product_name = f"{brand.title()} {category.replace('_', ' ').title()} {size}"
        
        events.append({
            "event_id": i + 1,
            "user_id": user["user_id"],
            "event_type": event_type,
            "main_category": category,
            "brand": brand,
            "price_range": price_range,
            "product_name": product_name,
            "search_query": f"{brand} {category}" if event_type == "search" else "",
            "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "synthetic",
            "session_id": f"sess_{random.randint(1000, 9999)}",
            "age_group": user["age_group"],
            "gender": user["gender"],
            "city": user["city"],
            "state": user["state"],
            "country": "India",
            "device_type": user["device_type"],
            "platform": user["platform"],
        })

    events.sort(key=lambda e: e["event_time"])
    return events

def main():
    print("Generating custom target data...")
    users = generate_users()
    events = generate_events(users, n_events=1500) # 1500 events across 6 users is robust

    fieldnames = list(events[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)
        
    print(f"Generated {len(events)} events for {len(users)} target users in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
