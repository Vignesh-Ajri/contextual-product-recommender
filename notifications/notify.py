import joblib
import pandas as pd
import mysql.connector
import re
import time
import logging
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("notify")


SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

INTEREST_SCORE_THRESHOLD = 3.0

MAX_EMAILS_PER_RUN = 50

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

CATEGORY_ICONS = {
    "electronics":       "📱",
    "computers":         "💻",
    "accessories":       "⌚",
    "appliances":        "🏠",
    "stationery":        "✏️",
    "clothing":          "👕",
    "footwear":          "👟",
    "sports":            "⚽",
    "toys":              "🧸",
    "beauty":            "💄",
    "health":            "💊",
    "grocery":           "🛒",
    "books":             "📚",
    "automotive":        "🚗",
    "furniture":         "🪑",
    "garden":            "🌿",
    "pet":               "🐾",
    "music":             "🎵",
    "gaming":            "🎮",
}


logger.info("Loading ML model...")
try:
    tfidf             = joblib.load("ml/tfidf.pkl")
    similarity_matrix = joblib.load("ml/cosine_sim.pkl")
    products_df       = pd.read_csv("ml/products.csv")
    logger.info(f"Model loaded — {len(products_df)} products")
except FileNotFoundError:
    logger.error("Model not found. Run ml/train_model.py first!")
    exit(1)


_db_conn = None

def get_db():
    """Get a MySQL connection with automatic reconnect on failure."""
    global _db_conn
    try:
        if _db_conn is not None and _db_conn.is_connected():
            return _db_conn
    except Exception:
        pass

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _db_conn = mysql.connector.connect(**DB_CONFIG)
            logger.info("MySQL connected")
            return _db_conn
        except mysql.connector.Error as e:
            logger.warning(f"DB connect attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY ** attempt)
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


def is_valid_email(email):
    """Validate email format. Returns False for None, empty, or malformed."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def get_user_name(email):
    """Safely extract user name from email. Falls back to 'there'."""
    try:
        if not email or "@" not in email:
            return "there"
        name = email.split("@")[0]
        name = name.replace(".", " ").replace("_", " ").replace("-", " ")
        return name.title() if name else "there"
    except Exception:
        return "there"


def find_similar(category, brand, top_n=3):
    """
    Given category + brand, find top N similar products.
    Used to fill the notification email with recommendations.
    """
    match = products_df[
        (products_df["main_category"] == category) &
        (products_df["brand"]         == brand)
    ]

    if len(match) == 0:
        match = products_df[products_df["main_category"] == category]

    if len(match) == 0:
        return []

    idx    = match.index[0]
    scores = list(enumerate(similarity_matrix[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = [s for s in scores if s[0] != idx]

    top = [products_df.iloc[s[0]] for s in scores[:top_n]]
    return [
        {
            "category":   str(p["main_category"]),
            "brand":      str(p["brand"]),
            "price_range": str(p["price_range"])
        }
        for p in top
    ]


def get_trending_products(top_n=3):
    """
    Fallback: return trending products when no personalized recs available.
    Picks top categories by frequency in the dataset.
    """
    if products_df is None or len(products_df) == 0:
        return []

    top_cats = products_df["main_category"].value_counts().head(top_n)
    trending = []
    for cat in top_cats.index:
        sample = products_df[products_df["main_category"] == cat].iloc[0]
        trending.append({
            "category":   str(sample["main_category"]),
            "brand":      str(sample["brand"]),
            "price_range": str(sample["price_range"])
        })
    return trending


def build_email_html(user_name, category, brand, recommendations, trigger_type):
    """
    Build a premium, responsive HTML email template.
    Different layouts for timeline vs interest triggers.
    """
    icon = CATEGORY_ICONS.get(category.lower(), "🛍️")

    rec_cards = ""
    for i, r in enumerate(recommendations, 1):
        r_icon = CATEGORY_ICONS.get(r["category"].lower(), "📦")
        rec_cards += f"""
        <tr>
            <td style="padding:14px 20px;border-bottom:1px solid #f0f0f0;">
                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                    <tr>
                        <td style="width:44px;vertical-align:middle;">
                            <div style="width:40px;height:40px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:10px;text-align:center;line-height:40px;font-size:18px;">
                                {r_icon}
                            </div>
                        </td>
                        <td style="padding-left:14px;vertical-align:middle;">
                            <div style="font-size:15px;font-weight:600;color:#1a1a2e;">{r['brand'].title()}</div>
                            <div style="font-size:13px;color:#666;margin-top:2px;">{r['category'].title()}</div>
                        </td>
                        <td style="text-align:right;vertical-align:middle;">
                            <span style="background:#f0f4ff;color:#4361ee;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;">
                                {r['price_range']}
                            </span>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """

    if trigger_type == "timeline":
        subject = f"Time to upgrade your {category}? Here are some picks for you!"
        intro_text = f"""
            <p style="font-size:16px;color:#333;line-height:1.6;margin:0 0 8px;">
                It looks like your <strong style="color:#4361ee;">{brand.title()} {category.title()}</strong> 
                might be due for a replacement.
            </p>
            <p style="font-size:14px;color:#666;line-height:1.5;margin:0;">
                Based on your purchase history, here are some products you might love:
            </p>
        """
        hero_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        hero_subtitle = "Your product lifecycle has completed"
    else:
        subject = f"Still thinking about {category}? Here are similar options!"
        intro_text = f"""
            <p style="font-size:16px;color:#333;line-height:1.6;margin:0 0 8px;">
                We noticed you've been checking out 
                <strong style="color:#4361ee;">{brand.title()} {category.title()}</strong> products.
            </p>
            <p style="font-size:14px;color:#666;line-height:1.5;margin:0;">
                Here are some alternatives you might be interested in:
            </p>
        """
        hero_gradient = "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
        hero_subtitle = "Based on your browsing activity"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f5f7fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

        <!-- Wrapper -->
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f5f7fa;">
            <tr>
                <td align="center" style="padding:32px 16px;">
                    <table cellpadding="0" cellspacing="0" border="0" width="580" style="max-width:580px;">

                        <!-- Header -->
                        <tr>
                            <td style="background:{hero_gradient};padding:40px 36px 32px;border-radius:16px 16px 0 0;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    <tr>
                                        <td>
                                            <div style="font-size:28px;margin-bottom:6px;">{icon}</div>
                                            <h1 style="margin:0;font-size:22px;font-weight:700;color:white;letter-spacing:-0.3px;">
                                                CPRP Recommender
                                            </h1>
                                            <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);letter-spacing:0.3px;">
                                                {hero_subtitle}
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="background:white;padding:36px;border-left:1px solid #e8ecf1;border-right:1px solid #e8ecf1;">
                                <p style="font-size:16px;color:#333;margin:0 0 20px;">
                                    Hi {user_name} 👋
                                </p>
                                {intro_text}
                            </td>
                        </tr>

                        <!-- Recommendations -->
                        <tr>
                            <td style="background:white;padding:0 36px;border-left:1px solid #e8ecf1;border-right:1px solid #e8ecf1;">
                                <div style="margin:20px 0 0;">
                                    <p style="font-size:12px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px;">
                                        Recommended for you
                                    </p>
                                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#fafbfd;border-radius:12px;border:1px solid #eef0f5;">
                                        {rec_cards}
                                    </table>
                                </div>
                            </td>
                        </tr>

                        <!-- CTA Button -->
                        <tr>
                            <td style="background:white;padding:28px 36px 36px;border-left:1px solid #e8ecf1;border-right:1px solid #e8ecf1;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    <tr>
                                        <td align="center">
                                            <a href="#" style="display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:14px 36px;border-radius:10px;font-size:15px;font-weight:600;text-decoration:none;letter-spacing:0.3px;">
                                                View More Recommendations →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background:#f8f9fb;padding:24px 36px;border-radius:0 0 16px 16px;border:1px solid #e8ecf1;border-top:none;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    <tr>
                                        <td>
                                            <p style="margin:0;font-size:12px;color:#999;line-height:1.6;">
                                                You received this because you previously interacted with {category.title()} products
                                                on our platform.
                                            </p>
                                            <p style="margin:8px 0 0;font-size:11px;color:#bbb;line-height:1.5;">
                                                CPRP — Contextual Product Recommender Platform<br>
                                                Academic Project · Vignesh · RIT MCA 2025-26<br>
                                                <a href="#" style="color:#999;text-decoration:underline;">Unsubscribe</a> · 
                                                <a href="#" style="color:#999;text-decoration:underline;">Preferences</a>
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>

    </body>
    </html>
    """

    return subject, html_content


def send_email(to_email, user_name, category, brand, recommendations, trigger_type):
    """
    Send a product recommendation email to the user.
    Includes retry logic with exponential backoff for rate limits.

    trigger_type = "timeline" or "interest"
    """

    if not is_valid_email(to_email):
        logger.warning(f"Invalid email skipped: {to_email!r}")
        return False

    if not recommendations:
        recommendations = get_trending_products()
        if not recommendations:
            logger.warning(f"No recommendations (even trending) for {to_email}")
            return False
        logger.info(f"Using trending fallback for {to_email}")

    subject, html_content = build_email_html(
        user_name, category, brand, recommendations, trigger_type
    )

    message = Mail(
        from_email    = (FROM_EMAIL, FROM_NAME),
        to_emails     = to_email,
        subject       = subject,
        html_content  = html_content
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sg       = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            logger.info(f"Email sent to {to_email} — Status: {response.status_code}")
            return True

        except Exception as e:
            error_str = str(e)

            is_retryable = "429" in error_str or "500" in error_str or "502" in error_str or "503" in error_str

            if is_retryable and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY ** attempt
                logger.warning(f"Retry {attempt}/{MAX_RETRIES} for {to_email} in {delay}s — {e}")
                time.sleep(delay)
            else:
                logger.error(f"Email failed to {to_email} (attempt {attempt}): {e}")
                return False

    return False


def log_notification(cursor, core_id, to_email, category, brand, recommendations, status):
    """Save a record of every notification sent."""
    rec_str = ", ".join([f"{r['brand']} {r['category']}" for r in recommendations])
    cursor.execute("""
        INSERT INTO notifications
            (core_id, channel, message, product_ids, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        core_id,
        "email",
        f"Recommendation for {category} — {brand}",
        rec_str,
        "sent" if status else "failed"
    ))


def was_notified_recently(cursor, core_id, category, hours=24):
    """
    Check if this user+category was notified within the last N hours.
    Prevents sending duplicate notifications.
    """
    cursor.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE core_id = %s
          AND message LIKE %s
          AND sent_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
          AND status = 'sent'
    """, (core_id, f"%{category}%", hours))
    count = cursor.fetchone()[0]
    return count > 0


def check_timeline_triggers():
    """
    Find users whose product lifetime has expired.
    Example: bought a pen 5 days ago → send notification today.

    Logic:
    - suppress_until is set when user purchases
    - When suppress_until date arrives → time to notify
    - We look for profiles where suppress_until is within today
    """
    logger.info("\n── Checking timeline triggers ───────────")

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            ip.core_id,
            ip.main_category,
            ip.brand,
            ip.price_range,
            ip.suppress_until,
            u.email
        FROM interest_profiles ip
        JOIN users u ON ip.core_id = u.core_id
        WHERE DATE(ip.suppress_until) <= DATE(NOW())
          AND ip.suppress_until IS NOT NULL
          AND u.email IS NOT NULL
          AND u.email != ''
    """)

    profiles = cursor.fetchall()
    logger.info(f"Found {len(profiles)} users ready for timeline notification")

    notified = 0
    skipped_invalid = 0
    skipped_duplicate = 0

    for p in profiles:
        if notified >= MAX_EMAILS_PER_RUN:
            logger.info(f"Batch limit reached ({MAX_EMAILS_PER_RUN}). Remaining deferred to next run.")
            break

        if not is_valid_email(p.get("email")):
            logger.warning(f"Skipping invalid email for user {p['core_id'][:8]}...")
            skipped_invalid += 1
            continue

        if was_notified_recently(cursor, p["core_id"], p["main_category"]):
            logger.info(f"Skipping {p['core_id'][:8]}... — already notified within 24h")
            skipped_duplicate += 1
            continue

        logger.info(f"\n  User: {p['core_id'][:8]}... | {p['main_category']} | {p['brand']}")

        recs = find_similar(p["main_category"], p["brand"])

        if not recs:
            recs = get_trending_products()
            if recs:
                logger.info(f"Using trending fallback (no similar products found)")
            else:
                logger.warning(f"No products available at all — skipping")
                continue

        user_name = get_user_name(p["email"])
        success = send_email(
            to_email     = p["email"],
            user_name    = user_name,
            category     = p["main_category"],
            brand        = p["brand"],
            recommendations = recs,
            trigger_type = "timeline"
        )

        log_notification(cursor, p["core_id"], p["email"],
                        p["main_category"], p["brand"], recs, success)

        cursor.execute("""
            UPDATE interest_profiles
            SET suppress_until = NULL
            WHERE core_id = %s AND main_category = %s AND brand = %s
        """, (p["core_id"], p["main_category"], p["brand"]))

        if success:
            notified += 1

    conn.commit()
    cursor.close()
    logger.info(f"\nTimeline — Sent: {notified} | Invalid: {skipped_invalid} | Duplicate: {skipped_duplicate}")


def check_event_triggers():
    """
    Find users who have crossed the interest score threshold but haven't bought.
    Send them a notification if they haven't been notified in the last 7 days.

    Logic:
    - interest_score >= 3.0
    - purchase_count = 0 (haven't bought yet)
    - suppress_until is NULL (not suppressed)
    - No notification sent in last 7 days (frequency capping via last_notified_at)
    """
    logger.info("\n── Checking event triggers ──────────────")

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            ip.core_id,
            ip.main_category,
            ip.brand,
            ip.price_range,
            ip.browse_count,
            ip.interest_score,
            u.email
        FROM interest_profiles ip
        JOIN users u ON ip.core_id = u.core_id
        WHERE ip.interest_score >= %s
          AND ip.purchase_count = 0
          AND ip.suppress_until IS NULL
          AND u.email IS NOT NULL
          AND u.email != ''
          AND (ip.last_notified_at IS NULL OR ip.last_notified_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
    """, (INTEREST_SCORE_THRESHOLD,))

    profiles = cursor.fetchall()
    logger.info(f"Found {len(profiles)} users showing strong interest")

    notified = 0
    skipped_invalid = 0
    skipped_duplicate = 0

    for p in profiles:
        if notified >= MAX_EMAILS_PER_RUN:
            logger.info(f"Batch limit reached ({MAX_EMAILS_PER_RUN}). Remaining deferred.")
            break

        if not is_valid_email(p.get("email")):
            logger.warning(f"Skipping invalid email for user {p['core_id'][:8]}...")
            skipped_invalid += 1
            continue

        if was_notified_recently(cursor, p["core_id"], p["main_category"]):
            logger.info(f"Skipping {p['core_id'][:8]}... — already notified within 24h")
            skipped_duplicate += 1
            continue

        logger.info(f"\n  User: {p['core_id'][:8]}... | {p['main_category']} | score {p['interest_score']:.1f}")

        recs = find_similar(p["main_category"], p["brand"])

        if not recs:
            recs = get_trending_products()
            if recs:
                logger.info(f"Using trending fallback")
            else:
                continue

        user_name = get_user_name(p["email"])
        success = send_email(
            to_email        = p["email"],
            user_name       = user_name,
            category        = p["main_category"],
            brand           = p["brand"],
            recommendations = recs,
            trigger_type    = "interest"
        )

        log_notification(cursor, p["core_id"], p["email"],
                        p["main_category"], p["brand"], recs, success)

        if success:
            cursor.execute("""
                UPDATE interest_profiles
                SET last_notified_at = NOW()
                WHERE core_id = %s AND main_category = %s AND brand = %s
            """, (p["core_id"], p["main_category"], p["brand"]))
            notified += 1

    conn.commit()
    cursor.close()
    logger.info(f"\nInterest — Sent: {notified} | Invalid: {skipped_invalid} | Duplicate: {skipped_duplicate}")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  CPRP - Notification Engine")
    logger.info(f"  Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Batch limit: {MAX_EMAILS_PER_RUN} emails/run")
    logger.info("=" * 50)

    try:
        check_timeline_triggers()
        check_event_triggers()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        safe_close_db()

    logger.info("\n── Complete ──────────────────────────────")
    logger.info("Run this daily or set up a scheduled task.")