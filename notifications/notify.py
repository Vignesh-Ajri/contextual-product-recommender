# ============================================================
# STEP 8 - Suppression Logic + Email Notification
# File: notifications/notify.py
#
# What this does:
# - Runs daily (like a cron job)
# - Checks MySQL for users whose product lifetime has expired
# - Skips users who are still in suppression period
# - Finds similar products using the ML model
# - Sends email notification via SendGrid
#
# Two triggers:
#   1. Timeline trigger  → pen bought 5 days ago → send notification
#   2. Event trigger     → user viewed same product 3+ times → send now
#
# Command: python notifications/notify.py
# ============================================================

import joblib
import pandas as pd
import mysql.connector
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from dotenv import load_dotenv
load_dotenv()

# ── 1. Configuration ──────────────────────────────────────────

# SendGrid API key
# Get free key from: https://sendgrid.com → sign up → Settings → API Keys
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")   # ← CHANGE THIS

# Email settings
FROM_EMAIL = os.getenv("FROM_EMAIL") # ← CHANGE THIS (verified in SendGrid)
FROM_NAME = os.getenv("FROM_NAME")

# MySQL config
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# Trigger threshold — how many views before we send immediate notification
VIEW_TRIGGER_COUNT = 3


# ── 2. Load ML model ──────────────────────────────────────────
print("Loading ML model...")
try:
    tfidf             = joblib.load("ml/tfidf.pkl")
    similarity_matrix = joblib.load("ml/cosine_sim.pkl")
    products_df       = pd.read_csv("ml/products.csv")
    print(f"✅ Model loaded — {len(products_df)} products")
except FileNotFoundError:
    print("❌ Model not found. Run ml/train_model.py first!")
    exit(1)


# ── 3. Database connection ────────────────────────────────────
def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# ── 4. Find similar products ──────────────────────────────────
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


# ── 5. Send email via SendGrid ────────────────────────────────
def send_email(to_email, user_name, category, brand, recommendations, trigger_type):
    """
    Send a product recommendation email to the user.

    trigger_type = "timeline" or "interest"
    """

    # Build recommendation list for email body
    rec_lines = ""
    for i, r in enumerate(recommendations, 1):
        rec_lines += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">
                {i}. {r['brand'].title()} — {r['category'].title()}
            </td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#666;">
                {r['price_range']}
            </td>
        </tr>
        """

    # Different subject based on trigger type
    if trigger_type == "timeline":
        subject = f"Time to upgrade your {category}? Here are some picks for you!"
        intro   = f"It looks like your <b>{brand.title()} {category}</b> might be due for a replacement."
    else:
        subject = f"Still thinking about {category}? Here are similar options!"
        intro   = f"We noticed you've been checking out <b>{brand.title()} {category}</b> products."

    # HTML email template
    html_content = f"""
    <html>
    <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">

        <div style="background:#4A90E2;padding:20px;border-radius:8px 8px 0 0;">
            <h2 style="color:white;margin:0;">CPRP Recommender</h2>
        </div>

        <div style="background:#f9f9f9;padding:20px;border:1px solid #eee;">
            <p>Hi {user_name},</p>
            <p>{intro}</p>
            <p>Here are some products you might like:</p>

            <table style="width:100%;border-collapse:collapse;background:white;border-radius:6px;">
                <thead>
                    <tr style="background:#4A90E2;color:white;">
                        <th style="padding:10px;text-align:left;">Product</th>
                        <th style="padding:10px;text-align:left;">Price Range</th>
                    </tr>
                </thead>
                <tbody>
                    {rec_lines}
                </tbody>
            </table>

            <p style="margin-top:20px;color:#666;font-size:12px;">
                You received this because you previously interacted with {category} products.
                <br>This is an academic project by Vignesh — RIT MCA 2025-26.
            </p>
        </div>

    </body>
    </html>
    """

    # Create and send email using SendGrid
    message = Mail(
        from_email    = (FROM_EMAIL, FROM_NAME),
        to_emails     = to_email,
        subject       = subject,
        html_content  = html_content
    )

    try:
        sg       = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"  📧 Email sent to {to_email} — Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"  ❌ Email failed to {to_email}: {e}")
        return False


# ── 6. Log notification to MySQL ──────────────────────────────
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


# ── 7. Timeline trigger ───────────────────────────────────────
def check_timeline_triggers():
    """
    Find users whose product lifetime has expired.
    Example: bought a pen 5 days ago → send notification today.

    Logic:
    - suppress_until is set when user purchases
    - When suppress_until date arrives → time to notify
    - We look for profiles where suppress_until is within today
    """
    print("\n── Checking timeline triggers ───────────")

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # Find profiles where suppress_until = today (lifetime just expired)
    # Using DATE() to compare just the date part, not time
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
    print(f"Found {len(profiles)} users ready for timeline notification")

    notified = 0
    for p in profiles:
        print(f"\n  User: {p['core_id'][:8]}... | {p['main_category']} | {p['brand']}")

        # Find similar products to recommend
        recs = find_similar(p["main_category"], p["brand"])

        if not recs:
            print(f"  ⚠️  No similar products found — skipping")
            continue

        # Send email
        success = send_email(
            to_email     = p["email"],
            user_name    = p["email"].split("@")[0],   # use email prefix as name
            category     = p["main_category"],
            brand        = p["brand"],
            recommendations = recs,
            trigger_type = "timeline"
        )

        # Log notification
        log_notification(cursor, p["core_id"], p["email"],
                        p["main_category"], p["brand"], recs, success)

        # Reset suppress_until so we don't send again immediately
        # Next notification will be triggered by new purchase or interest
        cursor.execute("""
            UPDATE interest_profiles
            SET suppress_until = NULL
            WHERE core_id = %s AND main_category = %s AND brand = %s
        """, (p["core_id"], p["main_category"], p["brand"]))

        if success:
            notified += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n✅ Timeline notifications sent: {notified}")


# ── 8. Event trigger ──────────────────────────────────────────
def check_event_triggers():
    """
    Find users who viewed the same product 3+ times but haven't bought.
    Send them a notification immediately — they are showing strong interest.

    Logic:
    - browse_count >= 3
    - purchase_count = 0 (haven't bought yet)
    - suppress_until is NULL (not suppressed)
    - No notification sent in last 3 days (avoid spam)
    """
    print("\n── Checking event triggers ──────────────")

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            ip.core_id,
            ip.main_category,
            ip.brand,
            ip.price_range,
            ip.browse_count,
            u.email
        FROM interest_profiles ip
        JOIN users u ON ip.core_id = u.core_id
        WHERE ip.browse_count >= %s
          AND ip.purchase_count = 0
          AND ip.suppress_until IS NULL
          AND u.email IS NOT NULL
          AND u.email != ''
          AND ip.core_id NOT IN (
              SELECT DISTINCT core_id FROM notifications
              WHERE sent_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
          )
    """, (VIEW_TRIGGER_COUNT,))

    profiles = cursor.fetchall()
    print(f"Found {len(profiles)} users showing strong interest")

    notified = 0
    for p in profiles:
        print(f"\n  User: {p['core_id'][:8]}... | {p['main_category']} | viewed {p['browse_count']}x")

        recs = find_similar(p["main_category"], p["brand"])

        if not recs:
            continue

        success = send_email(
            to_email        = p["email"],
            user_name       = p["email"].split("@")[0],
            category        = p["main_category"],
            brand           = p["brand"],
            recommendations = recs,
            trigger_type    = "interest"
        )

        log_notification(cursor, p["core_id"], p["email"],
                        p["main_category"], p["brand"], recs, success)

        if success:
            notified += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n✅ Interest notifications sent: {notified}")


# ── 9. Run both triggers ──────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  CPRP - Notification Engine")
    print(f"  Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    check_timeline_triggers()
    check_event_triggers()

    print("\n── Complete ──────────────────────────────")
    print("Run this daily or set up a scheduled task.")