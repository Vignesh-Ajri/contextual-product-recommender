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
# Edge cases handled:
#   - Malformed Kafka messages (missing fields validated)
#   - MySQL reconnection on connection drops
#   - Dead-letter logging for events that fail 3 times
#
# Run this BEFORE producer.py (start the postman before letters arrive)
# Command: python kafka/consumer.py
# ============================================================

import json           # json = parse incoming Kafka messages
import uuid           # uuid = generate unique IDs for new users
import logging
import time
import mysql.connector  # mysql.connector = connect to MySQL database
from datetime import datetime, timedelta  # for date calculations
from kafka import KafkaConsumer           # KafkaConsumer = listens to Kafka
import os
from dotenv import load_dotenv
load_dotenv()

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("consumer")

# ── 1. Configuration ──────────────────────────────────────────
KAFKA_SERVER = "localhost:9092"    # Kafka address
TOPIC_NAME   = "user_events"       # same topic the producer sends to
GROUP_ID     = "cprp_consumer"     # consumer group name (can be anything)

# MySQL connection settings
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# Retry/resilience config
MAX_DB_RETRIES = 3
DB_RETRY_DELAY = 2         # seconds (base for exponential backoff)
MAX_EVENT_RETRIES = 3       # max retries per event before dead-lettering

# Required fields in Kafka messages
REQUIRED_FIELDS = ["user_id"]
OPTIONAL_FIELDS = {
    "event_type":    "view",
    "main_category": "unknown",
    "brand":         "unknown",
    "price_range":   "unknown",
    "event_time":    None,        # will default to now()
    "source":        "kaggle"
}


# ── 2. Connect to MySQL with reconnect logic ─────────────────
_db_conn = None

def get_db_connection():
    """Create and return a MySQL connection with retry logic."""
    global _db_conn

    # Check if existing connection is alive
    try:
        if _db_conn is not None and _db_conn.is_connected():
            _db_conn.ping(reconnect=True, attempts=1, delay=0)
            return _db_conn
    except Exception:
        logger.warning("Existing DB connection lost, reconnecting...")
        _db_conn = None

    # Retry connection with exponential backoff
    for attempt in range(1, MAX_DB_RETRIES + 1):
        try:
            _db_conn = mysql.connector.connect(**DB_CONFIG)
            logger.info("MySQL connected")
            return _db_conn
        except mysql.connector.Error as e:
            logger.warning(f"DB connect attempt {attempt}/{MAX_DB_RETRIES} failed: {e}")
            if attempt < MAX_DB_RETRIES:
                delay = DB_RETRY_DELAY ** attempt
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error("Could not connect to MySQL after retries")
                raise


def safe_close_db():
    """Safely close the DB connection."""
    global _db_conn
    try:
        if _db_conn and _db_conn.is_connected():
            _db_conn.close()
    except Exception:
        pass
    _db_conn = None


# ── 3. Dead-letter logging ────────────────────────────────────
def log_dead_letter(event, error, attempt_count):
    """
    Log events that failed processing after max retries.
    In production, you'd send this to a dead-letter topic or DB table.
    """
    logger.error(
        f"DEAD LETTER — Event dropped after {attempt_count} attempts\n"
        f"Event: {json.dumps(event, default=str)[:500]}\n"
        f"Error: {error}"
    )
    # Optionally write to a dead-letter file
    try:
        with open("kafka/dead_letters.log", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {json.dumps(event, default=str)} | {error}\n")
    except Exception:
        pass  # Don't fail on dead-letter logging


# ── 4. Validate Kafka message ────────────────────────────────
def validate_event(event):
    """
    Validate incoming Kafka event. Returns (is_valid, cleaned_event, error_msg).
    Missing optional fields are filled with defaults.
    """
    if not isinstance(event, dict):
        return False, None, "Event is not a dict"

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in event or not event[field]:
            return False, None, f"Missing required field: {field}"

    # Fill optional fields with defaults
    cleaned = {}
    cleaned["user_id"] = str(event["user_id"]).strip()[:200]

    for field, default in OPTIONAL_FIELDS.items():
        value = event.get(field, default)
        if value is None:
            if field == "event_time":
                value = datetime.now().isoformat()
            else:
                value = default or "unknown"
        cleaned[field] = str(value).strip()[:200] if isinstance(value, str) else value

    # Validate event_type
    valid_types = {"view", "cart", "purchase"}
    if cleaned.get("event_type") not in valid_types:
        logger.warning(f"    Unknown event_type '{cleaned.get('event_type')}', defaulting to 'view'")
        cleaned["event_type"] = "view"

    return True, cleaned, None


# ── 5. Identity Resolution ────────────────────────────────────
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


# ── 6. Save Interaction ───────────────────────────────────────
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


# ── 7. Get product lifetime ───────────────────────────────────
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


# ── 8. Update Interest Profile ────────────────────────────────
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
        suppress_until = None
        if event_type == "purchase":
            lifetime = get_lifetime_days(cursor, category)
            suppress_until = datetime.now() + timedelta(days=lifetime)
            logger.info(f"Suppressing '{category}' for {lifetime} days (until {suppress_until.date()})")

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


# ── 9. Process one event (with retry) ─────────────────────────
def process_event(event):
    """
    Main function that handles one incoming Kafka event.
    Called once per message received from Kafka.
    Retries up to MAX_EVENT_RETRIES times before dead-lettering.
    """

    # Validate message structure
    is_valid, cleaned_event, error_msg = validate_event(event)
    if not is_valid:
        logger.warning(f"Malformed message skipped: {error_msg}")
        log_dead_letter(event, error_msg, 0)
        return

    event = cleaned_event

    for attempt in range(1, MAX_EVENT_RETRIES + 1):
        conn = None
        cursor = None
        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            user_id = event.get("user_id", "unknown")

            # Step A: Resolve identity (find or create core_id)
            core_id = resolve_identity(cursor, user_id)

            # Step B: Save the raw interaction
            save_interaction(cursor, core_id, event)

            # Step C: Update the interest profile
            update_interest_profile(cursor, core_id, event)

            # Commit all changes to MySQL
            conn.commit()

            logger.info(f"{event.get('event_type')} | user:{user_id} | "
                  f"{event.get('main_category')} | {event.get('brand')} | "
                  f"{event.get('price_range')}")
            return  # Success — exit retry loop

        except mysql.connector.Error as e:
            # MySQL-specific error — might be a dropped connection
            logger.warning(f"MySQL error (attempt {attempt}/{MAX_EVENT_RETRIES}): {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            # Force reconnect on next attempt
            safe_close_db()

            if attempt < MAX_EVENT_RETRIES:
                delay = DB_RETRY_DELAY ** attempt
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                log_dead_letter(event, str(e), attempt)

        except Exception as e:
            logger.error(f"Error processing event (attempt {attempt}/{MAX_EVENT_RETRIES}): {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass

            if attempt < MAX_EVENT_RETRIES:
                time.sleep(DB_RETRY_DELAY)
            else:
                log_dead_letter(event, str(e), attempt)

        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass


# ── 10. Start listening to Kafka ──────────────────────────────
def start_consumer():
    """
    Connect to Kafka and listen for incoming messages forever.
    This runs in a loop until you press Ctrl+C.
    """
    logger.info("Connecting to Kafka consumer...")

    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers = KAFKA_SERVER,
            group_id          = GROUP_ID,
            auto_offset_reset = "earliest",    # start from beginning of topic
            value_deserializer = lambda v: json.loads(v.decode("utf-8"))
            # value_deserializer = converts incoming bytes → JSON → Python dict
        )
        logger.info(f"Listening to topic: '{TOPIC_NAME}'")
        logger.info("Waiting for events... (Press Ctrl+C to stop)\n")

    except Exception as e:
        logger.error(f"Could not connect to Kafka: {e}")
        exit(1)

    # Loop forever — process every message that arrives
    processed = 0
    errors = 0
    for message in consumer:
        try:
            event = message.value       # the actual event dict
            process_event(event)
            processed += 1
        except json.JSONDecodeError as e:
            logger.warning(f"    Could not decode Kafka message: {e}")
            errors += 1
        except Exception as e:
            logger.error(f"Unexpected error on message: {e}")
            errors += 1

        # Print summary every 50 events
        if processed % 50 == 0 and processed > 0:
            logger.info(f"\n── {processed} events processed ({errors} errors) ──\n")


# ── 11. Run ───────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  CPRP - Kafka Consumer + Profile Builder")
    logger.info("=" * 50)
    try:
        start_consumer()
    except KeyboardInterrupt:
        logger.info("\n Consumer stopped by user")
    finally:
        safe_close_db()
        logger.info("Goodbye!")
