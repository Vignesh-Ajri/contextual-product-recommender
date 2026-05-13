import json
import uuid
import logging
import time
import mysql.connector
from datetime import datetime, timedelta
from kafka import KafkaConsumer
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("consumer")

KAFKA_SERVER    = "localhost:9092"
TOPIC_NAME      = "user_events"
GROUP_ID        = "cprp_consumer"
MAX_DB_RETRIES  = 3
DB_RETRY_DELAY  = 2
MAX_EVENT_RETRIES = 3

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME",     "cprp")
}

SCORE_WEIGHTS = {
    "view":     {"interest": 0.5, "browse": 0.5,  "engagement": 0.0, "purchase": 0.0},
    "search":   {"interest": 0.3, "browse": 0.2,  "engagement": 0.3, "purchase": 0.0},
    "cart":     {"interest": 1.0, "browse": 0.0,  "engagement": 1.0, "purchase": 0.0},
    "click":    {"interest": 0.4, "browse": 0.0,  "engagement": 0.4, "purchase": 0.0},
    "purchase": {"interest": 2.0, "browse": 0.0,  "engagement": 0.5, "purchase": 2.0},
    "dismiss":  {"interest": -1.0,"browse": 0.0,  "engagement": 0.0, "purchase": 0.0},
}

_db_conn = None

def get_db_connection():
    global _db_conn
    try:
        if _db_conn is not None and _db_conn.is_connected():
            _db_conn.ping(reconnect=True, attempts=1, delay=0)
            return _db_conn
    except Exception:
        _db_conn = None

    for attempt in range(1, MAX_DB_RETRIES + 1):
        try:
            _db_conn = mysql.connector.connect(**DB_CONFIG)
            return _db_conn
        except mysql.connector.Error as e:
            if attempt < MAX_DB_RETRIES:
                time.sleep(DB_RETRY_DELAY ** attempt)
            else:
                raise

def safe_close_db():
    global _db_conn
    try:
        if _db_conn and _db_conn.is_connected():
            _db_conn.close()
    except Exception:
        pass
    _db_conn = None


def log_dead_letter(event, error, attempt_count):
    logger.error(f"DEAD LETTER after {attempt_count} attempts: {error}")
    try:
        with open("kafka/dead_letters.log", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {json.dumps(event, default=str)} | {error}\n")
    except Exception:
        pass

def validate_event(event):
    if not isinstance(event, dict):
        return False, None, "Not a dict"
    if not event.get("user_id"):
        return False, None, "Missing user_id"

    cleaned = {
        "user_id":      str(event.get("user_id",      "")).strip()[:200],
        "event_type":   str(event.get("event_type",   "view")).strip().lower(),
        "main_category":str(event.get("main_category","unknown")).strip()[:100],
        "brand":        str(event.get("brand",        "unknown")).strip()[:100],
        "price_range":  str(event.get("price_range",  "unknown")).strip()[:50],
        "product_name": str(event.get("product_name", "")).strip()[:255],
        "search_query": str(event.get("search_query", "")).strip()[:255],
        "session_id":   str(event.get("session_id",   "")).strip()[:100],
        "event_time":   str(event.get("event_time",   datetime.now().isoformat())),
        "source":       str(event.get("source",       "api")).strip()[:100],
        "age_group":    str(event.get("age_group",    "")).strip()[:20],
        "gender":       str(event.get("gender",       "")).strip()[:20],
        "city":         str(event.get("city",         "")).strip()[:100],
        "state":        str(event.get("state",        "")).strip()[:100],
        "country":      str(event.get("country",      "India")).strip()[:50],
        "device_type":  str(event.get("device_type",  "")).strip()[:50],
        "platform":     str(event.get("platform",     "")).strip()[:50],
        "language":     str(event.get("language",     "")).strip()[:20],
    }

    valid_types = {"view", "search", "cart", "purchase", "dismiss", "click"}
    if cleaned["event_type"] not in valid_types:
        cleaned["event_type"] = "view"

    return True, cleaned, None


def resolve_identity(cursor, user_id, device_id=None):
    """
    Epsilon Layer 1: Link user_id and device_id to one Core ID.
    """
    cursor.execute(
        "SELECT core_id FROM identities WHERE identifier_type='user_id' AND identifier_value=%s",
        (str(user_id),)
    )
    result = cursor.fetchone()

    if result:
        core_id = result[0]
    else:
        core_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO users (core_id) VALUES (%s)", (core_id,))
        cursor.execute(
            "INSERT INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,%s,%s)",
            (core_id, "user_id", str(user_id))
        )

    if device_id and device_id.strip():
        cursor.execute(
            "SELECT id FROM identities WHERE identifier_type='device_id' AND identifier_value=%s",
            (str(device_id),)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT IGNORE INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,%s,%s)",
                (core_id, "device_id", str(device_id))
            )

    return core_id


def save_interaction(cursor, core_id, event):
    """
    Epsilon Layer 2: Save every behavioral event with full context.
    Includes search queries, session, device type.
    """
    cursor.execute("""
        INSERT INTO interactions
            (core_id, event_type, main_category, brand, price_range,
             product_name, search_query, session_id, device_type,
             event_time, source)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        core_id,
        event.get("event_type",    "view"),
        event.get("main_category", "unknown"),
        event.get("brand",         "unknown"),
        event.get("price_range",   "unknown"),
        event.get("product_name",  "") or None,
        event.get("search_query",  "") or None,
        event.get("session_id",    "") or None,
        event.get("device_type",   "") or None,
        event.get("event_time",    datetime.now().isoformat()),
        event.get("source",        "api")
    ))

def update_demographics(cursor, core_id, event):
    """
    Epsilon Layer 4: Store basic profile info sent by partner company.
    Only updates fields that are actually provided (not empty).
    """
    age_group   = event.get("age_group",   "")
    gender      = event.get("gender",      "")
    city        = event.get("city",        "")
    state       = event.get("state",       "")
    country     = event.get("country",     "India")
    device_type = event.get("device_type", "")
    platform    = event.get("platform",    "")
    language    = event.get("language",    "")

    if not any([age_group, gender, city, state, device_type, platform, language]):
        return

    cursor.execute(
        "SELECT demo_id FROM user_demographics WHERE core_id = %s",
        (core_id,)
    )
    existing = cursor.fetchone()

    if existing:
        updates = []
        values  = []
        if age_group:   updates.append("age_group=%s");   values.append(age_group)
        if gender:      updates.append("gender=%s");      values.append(gender)
        if city:        updates.append("city=%s");        values.append(city)
        if state:       updates.append("state=%s");       values.append(state)
        if country:     updates.append("country=%s");     values.append(country)
        if device_type: updates.append("device_type=%s"); values.append(device_type)
        if platform:    updates.append("platform=%s");    values.append(platform)
        if language:    updates.append("language=%s");    values.append(language)
        updates.append("updated_at=NOW()")
        values.append(core_id)

        cursor.execute(
            f"UPDATE user_demographics SET {', '.join(updates)} WHERE core_id=%s",
            values
        )
    else:
        cursor.execute("""
            INSERT INTO user_demographics
                (core_id, age_group, gender, city, state, country,
                 device_type, platform, language)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            core_id,
            age_group   or None,
            gender      or None,
            city        or None,
            state       or None,
            country     or "India",
            device_type or None,
            platform    or None,
            language    or None,
        ))


def update_interest_profile(cursor, core_id, event):
    """
    Epsilon Layers 3 + 5:
    - Layer 3: Track purchase counts, total spent
    - Layer 5: Update multi-dimensional interest scores
    """
    category    = event.get("main_category", "unknown")
    brand       = event.get("brand",         "unknown")
    price_range = event.get("price_range",   "unknown")
    event_type  = event.get("event_type",    "view")

    weights = SCORE_WEIGHTS.get(event_type, SCORE_WEIGHTS["view"])

    # FMCG / Personal care price ranges (INR)
    price_estimate_map = {
        "0-50": 25, "50-100": 75, "100-250": 175,
        "250-500": 375, "500-1000": 750, "1000-2000": 1500, "2000+": 3000,
        # Legacy ranges (backward compatibility)
        "0-500": 250, "500-1k": 750, "1k-5k": 3000,
    }
    estimated_price = price_estimate_map.get(price_range, 100)

    cursor.execute("""
        SELECT profile_id, interest_score, browse_score, purchase_score,
               engagement_score, browse_count, cart_count, purchase_count,
               dismiss_count, total_spent
        FROM interest_profiles
        WHERE core_id=%s AND main_category=%s AND brand=%s
    """, (core_id, category, brand))

    existing = cursor.fetchone()

    if existing:
        (profile_id, interest_score, browse_score, purchase_score,
         engagement_score, browse_count, cart_count, purchase_count,
         dismiss_count, total_spent) = existing

        # Update scores
        new_interest    = max(0, interest_score    + weights["interest"])
        new_browse      = max(0, browse_score      + weights["browse"])
        new_purchase_s  = max(0, purchase_score    + weights["purchase"])
        new_engagement  = max(0, engagement_score  + weights["engagement"])

        # Update counts
        new_browse_c    = browse_count    + (1 if event_type == "view"     else 0)
        new_cart_c      = cart_count      + (1 if event_type == "cart"     else 0)
        new_purchase_c  = purchase_count  + (1 if event_type == "purchase" else 0)
        new_dismiss_c   = dismiss_count   + (1 if event_type == "dismiss"  else 0)
        new_total_spent = (total_spent or 0) + (estimated_price if event_type == "purchase" else 0)

        # Calculate suppress_until
        suppress_until = None
        if event_type == "purchase":
            lifetime = get_lifetime_days(cursor, category)
            suppress_until = datetime.now() + timedelta(days=lifetime)
            logger.info(f"Suppressing '{category}' for {lifetime} days")
        elif event_type == "dismiss":
            suppress_until = datetime.now() + timedelta(days=7)
            logger.info(f"Dismissed — suppressing '{category}' for 7 days")

        cursor.execute("""
            UPDATE interest_profiles
            SET interest_score   = %s,
                browse_score     = %s,
                purchase_score   = %s,
                engagement_score = %s,
                browse_count     = %s,
                cart_count       = %s,
                purchase_count   = %s,
                dismiss_count    = %s,
                total_spent      = %s,
                last_purchased   = %s,
                suppress_until   = %s,
                updated_at       = NOW()
            WHERE profile_id = %s
        """, (
            new_interest, new_browse, new_purchase_s, new_engagement,
            new_browse_c, new_cart_c, new_purchase_c, new_dismiss_c,
            new_total_spent,
            datetime.now() if event_type == "purchase" else None,
            suppress_until,
            profile_id
        ))

    else:
        # New profile row
        suppress_until = None
        if event_type == "purchase":
            lifetime = get_lifetime_days(cursor, category)
            suppress_until = datetime.now() + timedelta(days=lifetime)
        elif event_type == "dismiss":
            suppress_until = datetime.now() + timedelta(days=7)

        cursor.execute("""
            INSERT INTO interest_profiles
                (core_id, main_category, brand, price_range,
                 interest_score, browse_score, purchase_score, engagement_score,
                 browse_count, cart_count, purchase_count, dismiss_count,
                 total_spent, last_purchased, suppress_until)
            VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s)
        """, (
            core_id, category, brand, price_range,
            weights["interest"], weights["browse"],
            weights["purchase"], weights["engagement"],
            1 if event_type == "view"     else 0,
            1 if event_type == "cart"     else 0,
            1 if event_type == "purchase" else 0,
            1 if event_type == "dismiss"  else 0,
            estimated_price if event_type == "purchase" else 0,
            datetime.now() if event_type == "purchase" else None,
            suppress_until
        ))


def get_lifetime_days(cursor, category):
    cursor.execute(
        "SELECT lifetime_days FROM product_lifetime WHERE main_category=%s",
        (category,)
    )
    result = cursor.fetchone()
    return result[0] if result else 90


def process_event(event):
    is_valid, cleaned_event, error_msg = validate_event(event)
    if not is_valid:
        log_dead_letter(event, error_msg, 0)
        return

    event = cleaned_event

    for attempt in range(1, MAX_EVENT_RETRIES + 1):
        conn = cursor = None
        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            user_id   = event.get("user_id",    "unknown")
            device_id = event.get("device_id",  "")

            core_id = resolve_identity(cursor, user_id, device_id)

            save_interaction(cursor, core_id, event)

            update_demographics(cursor, core_id, event)

            update_interest_profile(cursor, core_id, event)

            conn.commit()

            logger.info(
                f"{event.get('event_type'):8} | {event.get('main_category'):12} | "
                f"{event.get('brand'):10} | user:{user_id}"
            )
            return

        except mysql.connector.Error as e:
            logger.warning(f"MySQL error (attempt {attempt}): {e}")
            if conn:
                try: conn.rollback()
                except: pass
            safe_close_db()
            if attempt < MAX_EVENT_RETRIES:
                time.sleep(DB_RETRY_DELAY ** attempt)
            else:
                log_dead_letter(event, str(e), attempt)

        except Exception as e:
            logger.error(f"Error (attempt {attempt}): {e}")
            if conn:
                try: conn.rollback()
                except: pass
            if attempt < MAX_EVENT_RETRIES:
                time.sleep(DB_RETRY_DELAY)
            else:
                log_dead_letter(event, str(e), attempt)

        finally:
            if cursor:
                try: cursor.close()
                except: pass


def start_consumer():
    logger.info("Connecting to Kafka...")
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers  = KAFKA_SERVER,
            group_id           = GROUP_ID,
            auto_offset_reset  = "earliest",
            value_deserializer = lambda v: json.loads(v.decode("utf-8"))
        )
        logger.info(f"Listening to: '{TOPIC_NAME}'")
        logger.info("Waiting for events... (Ctrl+C to stop)\n")
    except Exception as e:
        logger.error(f"Could not connect to Kafka: {e}")
        exit(1)

    processed = errors = 0
    for message in consumer:
        try:
            process_event(message.value)
            processed += 1
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            errors += 1
        if processed % 50 == 0 and processed > 0:
            logger.info(f"── {processed} processed ({errors} errors) ──")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  CPRP — Consumer")
    logger.info("=" * 50)
    try:
        start_consumer()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        safe_close_db()
        logger.info("Goodbye!")