# ============================================================
# STEP 4 - Kafka Consumer + Profile Builder
# File: kafka/consumer.py
#
# What this does:
# - Listens to Kafka topic "user_events" continuously
# - For each event received:
#     1. Creates/finds a user in MySQL (Identity Resolution)
#     2. Saves the interaction (view/cart/purchase)
#     3. Updates the user's interest profile (4 parameters)
#     4. If purchase → sets suppression date using product lifetime
# - Think of it as: "postman picking up letters and delivering them"
#
# Run this BEFORE producer.py (start the postman before letters arrive)
# Command: python kafka/consumer.py
# ============================================================

import json           # json = parse incoming Kafka messages
import uuid           # uuid = generate unique IDs for new users
import mysql.connector  # mysql.connector = connect to MySQL database
from datetime import datetime, timedelta  # for date calculations
from kafka import KafkaConsumer           # KafkaConsumer = listens to Kafka
import os
from dotenv import load_dotenv
load_dotenv()

# ── 1. Configuration ──────────────────────────────────────────
KAFKA_SERVER = "localhost:9092"    # Kafka address
TOPIC_NAME   = "user_events"       # same topic the producer sends to
GROUP_ID     = "cprp_consumer"     # consumer group name (can be anything)

# MySQL connection settings
# Change password to whatever you set during MySQL installation
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# ── 2. Connect to MySQL ───────────────────────────────────────
def get_db_connection():
    """Create and return a MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        print("Make sure MySQL is running and password is correct in DB_CONFIG")
        exit(1)


# ── 3. Identity Resolution ────────────────────────────────────
def resolve_identity(cursor, user_id):
    """
    Find or create a core_id for this user_id.

    This is your Identity Resolution module from the report.
    - If we've seen this user_id before → return their existing core_id
    - If new user → create a new UUID core_id and save it
    """

    # Check if this user_id already exists in identities table
    cursor.execute(
        "SELECT core_id FROM identities WHERE identifier_type = 'user_id' AND identifier_value = %s",
        (str(user_id),)
    )
    result = cursor.fetchone()

    if result:
        # User already exists — return their core_id
        return result[0]

    else:
        # New user — create a fresh UUID as core_id
        new_core_id = str(uuid.uuid4())   # generates something like "a1b2-c3d4-..."

        # Insert into users table (master record)
        cursor.execute(
            "INSERT INTO users (core_id) VALUES (%s)",
            (new_core_id,)
        )

        # Insert into identities table (link user_id → core_id)
        cursor.execute(
            "INSERT INTO identities (core_id, identifier_type, identifier_value) VALUES (%s, %s, %s)",
            (new_core_id, "user_id", str(user_id))
        )

        return new_core_id


# ── 4. Save Interaction ───────────────────────────────────────
def save_interaction(cursor, core_id, event):
    """
    Save one event (view/cart/purchase) to interactions table.
    Every single action by the user is recorded here.
    """
    cursor.execute("""
        INSERT INTO interactions
            (core_id, event_type, main_category, brand, price_range, event_time, source)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s)
    """, (
        core_id,
        event.get("event_type",    "view"),
        event.get("main_category", "unknown"),
        event.get("brand",         "unknown"),
        event.get("price_range",   "unknown"),
        event.get("event_time",    datetime.now().isoformat()),
        event.get("source",        "kaggle")
    ))


# ── 5. Get product lifetime ───────────────────────────────────
def get_lifetime_days(cursor, category):
    """
    Look up how many days this product category lasts.
    Example: stationery = 5 days, electronics = 1095 days
    """
    cursor.execute(
        "SELECT lifetime_days FROM product_lifetime WHERE main_category = %s",
        (category,)
    )
    result = cursor.fetchone()

    if result:
        return result[0]
    else:
        return 90   # default 90 days if category not in table


# ── 6. Update Interest Profile ────────────────────────────────
def update_interest_profile(cursor, core_id, event):
    """
    Update what the user is interested in.

    This builds your 4-parameter profile:
    - main_category (electronics, stationery...)
    - brand         (samsung, parker...)
    - price_range   (50k-70k, 0-500...)
    - browse_count  (how many times viewed)

    Scoring logic:
    - view     → interest_score + 0.5
    - cart     → interest_score + 1.0  (stronger signal)
    - purchase → interest_score + 2.0  (strongest signal) + set suppress date
    """

    category   = event.get("main_category", "unknown")
    brand      = event.get("brand",         "unknown")
    price_range = event.get("price_range",  "unknown")
    event_type = event.get("event_type",    "view")

    # Score to add based on event type
    score_map = {
        "view":     0.5,
        "cart":     1.0,
        "purchase": 2.0
    }
    score_delta = score_map.get(event_type, 0.5)

    # Check if profile row already exists for this user+category+brand
    cursor.execute("""
        SELECT profile_id, interest_score, browse_count, purchase_count
        FROM interest_profiles
        WHERE core_id = %s AND main_category = %s AND brand = %s
    """, (core_id, category, brand))

    existing = cursor.fetchone()

    if existing:
        # Profile exists — UPDATE it
        profile_id     = existing[0]
        new_score      = existing[1] + score_delta
        new_browse     = existing[2] + (1 if event_type == "view" else 0)
        new_purchase   = existing[3] + (1 if event_type == "purchase" else 0)

        # If purchase → calculate suppress_until date
        # "Don't recommend this category for X days after purchase"
        suppress_until = None
        if event_type == "purchase":
            lifetime = get_lifetime_days(cursor, category)
            suppress_until = datetime.now() + timedelta(days=lifetime)
            print(f"  🔇 Suppressing '{category}' for {lifetime} days (until {suppress_until.date()})")

        if suppress_until:
            cursor.execute("""
                UPDATE interest_profiles
                SET interest_score  = %s,
                    browse_count    = %s,
                    purchase_count  = %s,
                    last_purchased  = NOW(),
                    suppress_until  = %s,
                    updated_at      = NOW()
                WHERE profile_id = %s
            """, (new_score, new_browse, new_purchase, suppress_until, profile_id))
        else:
            cursor.execute("""
                UPDATE interest_profiles
                SET interest_score = %s,
                    browse_count   = %s,
                    purchase_count = %s,
                    updated_at     = NOW()
                WHERE profile_id = %s
            """, (new_score, new_browse, new_purchase, profile_id))

    else:
        # New profile row — INSERT it
        suppress_until = None
        if event_type == "purchase":
            lifetime = get_lifetime_days(cursor, category)
            suppress_until = datetime.now() + timedelta(days=lifetime)

        cursor.execute("""
            INSERT INTO interest_profiles
                (core_id, main_category, brand, price_range,
                 interest_score, browse_count, purchase_count,
                 last_purchased, suppress_until)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            core_id,
            category,
            brand,
            price_range,
            score_delta,                                          # starting score
            1 if event_type == "view" else 0,                    # browse count
            1 if event_type == "purchase" else 0,                # purchase count
            datetime.now() if event_type == "purchase" else None, # last purchased
            suppress_until                                        # suppress date
        ))


# ── 7. Process one event ──────────────────────────────────────
def process_event(event):
    """
    Main function that handles one incoming Kafka event.
    Called once per message received from Kafka.
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = event.get("user_id", "unknown")

        # Step A: Resolve identity (find or create core_id)
        core_id = resolve_identity(cursor, user_id)

        # Step B: Save the raw interaction
        save_interaction(cursor, core_id, event)

        # Step C: Update the interest profile
        update_interest_profile(cursor, core_id, event)

        # Commit all changes to MySQL
        conn.commit()

        print(f"  ✅ {event.get('event_type')} | user:{user_id} | "
              f"{event.get('main_category')} | {event.get('brand')} | "
              f"{event.get('price_range')}")

    except Exception as e:
        conn.rollback()   # undo changes if anything went wrong
        print(f"  ❌ Error processing event: {e}")

    finally:
        cursor.close()
        conn.close()     # always close connection after done


# ── 8. Start listening to Kafka ───────────────────────────────
def start_consumer():
    """
    Connect to Kafka and listen for incoming messages forever.
    This runs in a loop until you press Ctrl+C.
    """
    print("Connecting to Kafka consumer...")

    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers = KAFKA_SERVER,
            group_id          = GROUP_ID,
            auto_offset_reset = "earliest",    # start from beginning of topic
            value_deserializer = lambda v: json.loads(v.decode("utf-8"))
            # value_deserializer = converts incoming bytes → JSON → Python dict
        )
        print(f"✅ Listening to topic: '{TOPIC_NAME}'")
        print("Waiting for events... (Press Ctrl+C to stop)\n")

    except Exception as e:
        print(f"❌ Could not connect to Kafka: {e}")
        exit(1)

    # Loop forever — process every message that arrives
    processed = 0
    for message in consumer:
        event = message.value       # the actual event dict
        process_event(event)
        processed += 1

        # Print summary every 50 events
        if processed % 50 == 0:
            print(f"\n── {processed} events processed so far ──\n")


# ── 9. Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  CPRP - Kafka Consumer + Profile Builder")
    print("=" * 50)
    start_consumer()
