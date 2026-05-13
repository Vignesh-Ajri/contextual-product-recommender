"""
CPRP — Synthetic FMCG / Personal Care Data Generator
Generates realistic user behavior data for testing
the recommendation engine with daily-use consumer products.

Usage:
    python data/generate_fmcg_data.py
    python data/generate_fmcg_data.py --rows 50000

Output: data/fmcg_events.csv
"""

import csv
import random
import sys
from datetime import datetime, timedelta

OUTPUT_FILE = "data/fmcg_events.csv"
DEFAULT_ROWS = 20000

# ── FMCG Product Catalog ─────────────────────────────────────
PRODUCTS = {
    # Oral Care
    "toothpaste": {
        "brands": ["colgate", "sensodyne", "pepsodent", "closeup", "dabur", "patanjali", "oral-b"],
        "price_ranges": ["50-100", "100-250", "250-500"],
        "weight": 15,  # Higher weight = more likely to appear
    },
    "toothbrush": {
        "brands": ["colgate", "oral-b", "sensodyne", "pepsodent", "aquafresh"],
        "price_ranges": ["0-50", "50-100", "100-250"],
        "weight": 10,
    },
    "mouthwash": {
        "brands": ["listerine", "colgate", "closeup", "betadine"],
        "price_ranges": ["100-250", "250-500"],
        "weight": 5,
    },

    # Hair Care
    "shampoo": {
        "brands": ["head-shoulders", "dove", "tresemme", "pantene", "clinic-plus", "sunsilk", "loreal"],
        "price_ranges": ["100-250", "250-500", "500-1000"],
        "weight": 12,
    },
    "conditioner": {
        "brands": ["dove", "tresemme", "pantene", "loreal", "matrix"],
        "price_ranges": ["100-250", "250-500", "500-1000"],
        "weight": 6,
    },
    "hair_oil": {
        "brands": ["parachute", "dabur", "bajaj", "keo-karpin", "indulekha"],
        "price_ranges": ["50-100", "100-250", "250-500"],
        "weight": 8,
    },

    # Skin Care
    "face_wash": {
        "brands": ["himalaya", "cetaphil", "neutrogena", "garnier", "clean-clear", "nivea", "pond's"],
        "price_ranges": ["100-250", "250-500"],
        "weight": 10,
    },
    "moisturizer": {
        "brands": ["nivea", "cetaphil", "pond's", "vaseline", "himalaya", "neutrogena"],
        "price_ranges": ["100-250", "250-500", "500-1000"],
        "weight": 8,
    },
    "sunscreen": {
        "brands": ["neutrogena", "lakme", "lotus", "mamaearth", "minimalist", "cetaphil"],
        "price_ranges": ["250-500", "500-1000"],
        "weight": 7,
    },
    "body_lotion": {
        "brands": ["nivea", "vaseline", "dove", "jergens", "aveeno"],
        "price_ranges": ["100-250", "250-500"],
        "weight": 6,
    },
    "lip_balm": {
        "brands": ["nivea", "maybelline", "vaseline", "himalaya", "burt's-bees"],
        "price_ranges": ["50-100", "100-250"],
        "weight": 5,
    },

    # Cosmetics
    "lipstick": {
        "brands": ["maybelline", "lakme", "mac", "nykaa", "colorbar", "sugar", "faces-canada"],
        "price_ranges": ["250-500", "500-1000", "1000-2000"],
        "weight": 8,
    },
    "foundation": {
        "brands": ["maybelline", "lakme", "mac", "loreal", "nykaa"],
        "price_ranges": ["250-500", "500-1000", "1000-2000"],
        "weight": 5,
    },
    "mascara": {
        "brands": ["maybelline", "lakme", "mac", "colorbar"],
        "price_ranges": ["250-500", "500-1000"],
        "weight": 4,
    },
    "compact_powder": {
        "brands": ["lakme", "maybelline", "pond's", "faces-canada"],
        "price_ranges": ["100-250", "250-500", "500-1000"],
        "weight": 4,
    },

    # Personal Care
    "soap": {
        "brands": ["dove", "lux", "dettol", "lifebuoy", "pears", "fiama", "nivea"],
        "price_ranges": ["0-50", "50-100", "100-250"],
        "weight": 12,
    },
    "deodorant": {
        "brands": ["nivea", "dove", "axe", "fogg", "wildstone", "park-avenue", "engage"],
        "price_ranges": ["100-250", "250-500"],
        "weight": 8,
    },
    "razor": {
        "brands": ["gillette", "park-avenue", "vi-john"],
        "price_ranges": ["50-100", "100-250", "250-500"],
        "weight": 5,
    },
    "hand_sanitizer": {
        "brands": ["dettol", "lifebuoy", "himalaya", "sterillium"],
        "price_ranges": ["50-100", "100-250"],
        "weight": 4,
    },

    # Household
    "detergent": {
        "brands": ["surf-excel", "ariel", "tide", "rin", "nirma", "henko"],
        "price_ranges": ["50-100", "100-250", "250-500"],
        "weight": 10,
    },
    "dishwash": {
        "brands": ["vim", "exo", "pril"],
        "price_ranges": ["50-100", "100-250"],
        "weight": 6,
    },
    "floor_cleaner": {
        "brands": ["lizol", "harpic", "domex", "presto"],
        "price_ranges": ["100-250", "250-500"],
        "weight": 5,
    },
}

EVENT_TYPES = ["view", "view", "view", "view", "cart", "purchase", "search", "click", "dismiss"]
# view is weighted 4x more because browsing is the most common action

CITIES = [
    ("Bengaluru", "Karnataka"), ("Mumbai", "Maharashtra"), ("Delhi", "Delhi"),
    ("Chennai", "Tamil Nadu"), ("Hyderabad", "Telangana"), ("Pune", "Maharashtra"),
    ("Kolkata", "West Bengal"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Kochi", "Kerala"), ("Coimbatore", "Tamil Nadu"),
]

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["male", "female", "other"]
DEVICES = ["mobile", "desktop", "tablet"]
PLATFORMS = ["android", "ios", "web"]


def weighted_category_pick():
    """Pick a category weighted by its frequency weight."""
    categories = list(PRODUCTS.keys())
    weights = [PRODUCTS[c]["weight"] for c in categories]
    return random.choices(categories, weights=weights, k=1)[0]


def generate_user_pool(n_users=500):
    """Create a pool of synthetic users with stable demographics."""
    users = []
    for i in range(1, n_users + 1):
        city, state = random.choice(CITIES)
        users.append({
            "user_id": f"user_{i:04d}",
            "age_group": random.choice(AGE_GROUPS),
            "gender": random.choice(GENDERS),
            "city": city,
            "state": state,
            "device_type": random.choice(DEVICES),
            "platform": random.choice(PLATFORMS),
            # Each user has 2-4 preferred categories (natural behavior)
            "preferred_categories": random.sample(
                list(PRODUCTS.keys()),
                k=random.randint(2, 5)
            ),
        })
    return users


def generate_events(users, n_events=20000):
    """Generate realistic behavioral events."""
    events = []
    base_time = datetime.now() - timedelta(days=45)  # Events over last 45 days

    for i in range(n_events):
        user = random.choice(users)

        # 70% chance user interacts with their preferred categories
        if random.random() < 0.7:
            category = random.choice(user["preferred_categories"])
        else:
            category = weighted_category_pick()

        product = PRODUCTS[category]
        brand = random.choice(product["brands"])
        price_range = random.choice(product["price_ranges"])
        event_type = random.choice(EVENT_TYPES)

        # More recent events are more likely (recency bias in generation)
        days_ago = int(random.triangular(0, 45, 5))  # Skewed toward recent
        hours_offset = random.randint(0, 23)
        event_time = base_time + timedelta(days=45 - days_ago, hours=hours_offset)

        # Generate search queries for search events
        search_query = ""
        if event_type == "search":
            search_templates = [
                f"best {category}", f"{brand} {category}",
                f"cheap {category}", f"{category} for {user['gender']}",
                f"{brand} {category} price", f"top {category} india",
            ]
            search_query = random.choice(search_templates)

        product_name = f"{brand.title()} {category.replace('_', ' ').title()}"

        events.append({
            "event_id": i + 1,
            "user_id": user["user_id"],
            "event_type": event_type,
            "main_category": category,
            "brand": brand,
            "price_range": price_range,
            "product_name": product_name,
            "search_query": search_query,
            "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "synthetic",
            "session_id": f"sess_{random.randint(10000, 99999)}",
            "age_group": user["age_group"],
            "gender": user["gender"],
            "city": user["city"],
            "state": user["state"],
            "country": "India",
            "device_type": user["device_type"],
            "platform": user["platform"],
        })

    # Sort by event_time
    events.sort(key=lambda e: e["event_time"])
    return events


def main():
    n_rows = DEFAULT_ROWS
    if "--rows" in sys.argv:
        idx = sys.argv.index("--rows")
        if idx + 1 < len(sys.argv):
            n_rows = int(sys.argv[idx + 1])

    print("=" * 55)
    print("  CPRP — FMCG Data Generator")
    print("=" * 55)

    print(f"\nGenerating {n_rows} synthetic FMCG events...")
    print(f"Product categories: {len(PRODUCTS)}")
    print(f"Total brands: {sum(len(p['brands']) for p in PRODUCTS.values())}")

    users = generate_user_pool(n_users=500)
    print(f"User pool: {len(users)} synthetic users")

    events = generate_events(users, n_events=n_rows)

    # Write CSV
    fieldnames = list(events[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)

    print(f"\nSaved to: {OUTPUT_FILE}")
    print(f"Total events: {len(events)}")

    # Summary
    from collections import Counter
    cat_counts = Counter(e["main_category"] for e in events)
    type_counts = Counter(e["event_type"] for e in events)

    print(f"\n-- Event Type Distribution --")
    for et, cnt in type_counts.most_common():
        print(f"  {et:10} {cnt:6d}  ({cnt/len(events)*100:.1f}%)")

    print(f"\n-- Top 10 Categories --")
    for cat, cnt in cat_counts.most_common(10):
        print(f"  {cat:18} {cnt:6d}")

    print(f"\n-- Done --")


if __name__ == "__main__":
    main()
