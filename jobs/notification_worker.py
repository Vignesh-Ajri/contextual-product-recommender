import os
import smtplib
import logging
import mysql.connector
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 3307)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
FROM_EMAIL     = GMAIL_USER


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def get_user_email(cursor, core_id):
    cursor.execute("SELECT email FROM users WHERE core_id=%s", (core_id,))
    res = cursor.fetchone()
    return res["email"] if res and res["email"] else None


def build_html(title, intro, body, cta_text="Shop Now", cta_url="http://localhost:3000/products"):
    """Build a clean, styled HTML email."""
    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>" + title + "</title></head>"
        "<body style='margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;'>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='padding:40px 0;'>"
        "<tr><td align='center'><table width='580' cellpadding='0' cellspacing='0'"
        " style='background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);'>"
        "<tr><td style='background:linear-gradient(135deg,#2563eb,#7c3aed);padding:32px 40px;text-align:center;'>"
        "<h1 style='color:#fff;margin:0;font-size:24px;'>&#128717; SmartShop</h1>"
        "<p style='color:rgba(255,255,255,.8);margin:4px 0 0;font-size:13px;'>Powered by CPRP Intelligence</p>"
        "</td></tr>"
        "<tr><td style='padding:40px;'>"
        "<h2 style='color:#111827;margin:0 0 12px;font-size:20px;font-weight:700;'>" + title + "</h2>"
        "<p style='color:#6b7280;font-size:15px;line-height:1.6;margin:0 0 16px;'>" + intro + "</p>"
        "<div style='background:#f9fafb;border-left:4px solid #2563eb;border-radius:8px;padding:16px 20px;margin:24px 0;'>"
        "<p style='color:#374151;font-size:15px;line-height:1.6;margin:0;'>" + body + "</p></div>"
        "<div style='text-align:center;margin:32px 0;'>"
        "<a href='" + cta_url + "' style='background:#2563eb;color:#fff;text-decoration:none;"
        "font-weight:600;font-size:15px;padding:14px 36px;border-radius:50px;display:inline-block;'>"
        + cta_text + " &#8594;</a></div></td></tr>"
        "<tr><td style='background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;text-align:center;'>"
        "<p style='color:#9ca3af;font-size:12px;margin:0;'>You received this from SmartShop."
        " Powered by CPRP Engine.</p></td></tr>"
        "</table></td></tr></table></body></html>"
    )


def send_email(to_email, subject, html_content):
    """Send email via Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        logger.warning("[DRY RUN] Gmail credentials not set. Would send to %s: %s", to_email, subject)
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"SmartShop <{FROM_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception as e:
        logger.error("Failed to send to %s: %s", to_email, e)
        return False


def mark_notified(cursor, db, profile_id):
    cursor.execute("UPDATE interest_profiles SET last_notified_at=NOW() WHERE profile_id=%s", (profile_id,))
    db.commit()


def run_engine():
    logger.info("=" * 55)
    logger.info("  CPRP Notification Engine (Gmail SMTP)")
    logger.info("  FROM: %s", FROM_EMAIL)
    logger.info("=" * 55)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    sent = 0

    try:
        # ── Rule 1: Replenishment reminders ──────────────────────────
        logger.info("Rule 1: Replenishment reminders...")
        cursor.execute("""
            SELECT ip.profile_id, ip.core_id, ip.main_category, ip.brand,
                   ip.last_purchased, pl.lifetime_days
            FROM interest_profiles ip
            JOIN product_lifetime pl ON ip.main_category = pl.main_category
            WHERE ip.last_purchased IS NOT NULL
              AND ip.suppress_until IS NULL
              AND NOW() >= DATE_ADD(ip.last_purchased, INTERVAL (pl.lifetime_days - 2) DAY)
              AND (ip.last_notified_at IS NULL
                   OR ip.last_notified_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        """)
        rows = cursor.fetchall()
        logger.info("  Found %d replenishment candidates.", len(rows))
        for r in rows:
            email = get_user_email(cursor, r["core_id"])
            if not email:
                logger.warning("  No email for %s — skipping.", r["core_id"])
                continue
            cat   = r["main_category"].replace("_", " ").title()
            brand = r["brand"].title()
            html = build_html(
                title="Time to restock your " + cat + "?",
                intro="Hi! It has been about " + str(r["lifetime_days"]) + " days since you bought " + brand + " " + cat + ".",
                body="Running low? Your " + brand + " " + cat + " is likely due for a restock. Fresh stock is ready!",
                cta_text="Restock " + cat,
            )
            if send_email(email, "Time to restock your " + brand + " " + cat + "?", html):
                mark_notified(cursor, db, r["profile_id"])
                sent += 1

        # ── Rule 2: High-interest spike alerts ───────────────────────
        logger.info("Rule 2: High-interest alerts...")
        cursor.execute("""
            SELECT profile_id, core_id, main_category, brand, interest_score
            FROM interest_profiles
            WHERE interest_score >= 3.0
              AND (last_notified_at IS NULL
                   OR last_notified_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        """)
        rows = cursor.fetchall()
        logger.info("  Found %d high-interest candidates.", len(rows))
        for r in rows:
            email = get_user_email(cursor, r["core_id"])
            if not email:
                logger.warning("  No email for %s — skipping.", r["core_id"])
                continue
            cat   = r["main_category"].replace("_", " ").title()
            brand = r["brand"].title()
            html = build_html(
                title="We noticed you like " + cat + "!",
                intro="Hi! Our AI engine spotted you have been exploring " + brand + " " + cat + " recently.",
                body="Your interest score for " + brand + " " + cat + " is one of the highest we have seen. Do not let it sell out!",
                cta_text="View " + cat + " Products",
            )
            if send_email(email, "Still thinking about " + brand + " " + cat + "?", html):
                mark_notified(cursor, db, r["profile_id"])
                sent += 1

        # ── Rule 3: New product alerts ────────────────────────────────
        logger.info("Rule 3: New product alerts...")
        cursor.execute("""
            SELECT ip.profile_id, ip.core_id, ip.main_category,
                   p.brand AS new_brand, p.price_range
            FROM interest_profiles ip
            JOIN products p ON ip.main_category = p.main_category
                           AND ip.price_range = p.price_range
            WHERE p.created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
              AND ip.interest_score >= 2.0
              AND ip.purchase_count = 0
              AND (ip.suppress_until IS NULL OR ip.suppress_until < NOW())
              AND (ip.last_notified_at IS NULL
                   OR ip.last_notified_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        """)
        rows = cursor.fetchall()
        logger.info("  Found %d new-product alert candidates.", len(rows))
        for r in rows:
            email = get_user_email(cursor, r["core_id"])
            if not email:
                continue
            cat   = r["main_category"].replace("_", " ").title()
            brand = r["new_brand"].title()
            html = build_html(
                title="New " + cat + " arrival for you!",
                intro="Hi! A brand-new " + cat + " from " + brand + " just landed on SmartShop.",
                body="We matched this to your interests and budget. Check it out before it sells out!",
                cta_text="See New " + cat,
            )
            if send_email(email, "New Arrival: " + brand + " " + cat + " just dropped!", html):
                mark_notified(cursor, db, r["profile_id"])
                sent += 1

        logger.info("=" * 55)
        logger.info("  Done. Total emails sent: %d", sent)
        logger.info("=" * 55)

    except Exception as e:
        logger.error("Error in engine: %s", e, exc_info=True)
    finally:
        cursor.close()
        db.close()


if __name__ == "__main__":
    run_engine()
