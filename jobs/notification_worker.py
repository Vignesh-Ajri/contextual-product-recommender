import os
import sys
import logging
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 3307)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@cprp-engine.com")

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def get_user_email(cursor, core_id):
    """Retrieve the stored email for a core_id."""
    cursor.execute("SELECT email FROM users WHERE core_id=%s", (core_id,))
    res = cursor.fetchone()
    return res['email'] if res and res['email'] else None

def send_sendgrid_email(to_email, subject, content):
    """Sends an email using the SendGrid API."""
    if not SENDGRID_API_KEY:
        logger.warning(f"[DRY RUN] Would send email to {to_email}: {subject}")
        return True

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=f"<strong>{content}</strong>"
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}. Status code: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def update_last_notified(cursor, db, profile_id):
    cursor.execute("UPDATE interest_profiles SET last_notified_at = NOW() WHERE profile_id = %s", (profile_id,))
    db.commit()

def run_engine():
    logger.info("Starting CPRP Notification Engine (SendGrid)")
    db = get_db()
    cursor = db.cursor(dictionary=True)

    notifications_sent = 0

    try:
        # RULE 1: Replenishment Lifetime Reminders
        cursor.execute("""
            SELECT 
                ip.profile_id, ip.core_id, ip.main_category, ip.brand, ip.last_purchased,
                pl.lifetime_days
            FROM interest_profiles ip
            JOIN product_lifetime pl ON ip.main_category = pl.main_category
            WHERE ip.last_purchased IS NOT NULL 
              AND ip.suppress_until IS NULL
              AND NOW() >= DATE_ADD(ip.last_purchased, INTERVAL (pl.lifetime_days - 2) DAY)
              AND (ip.last_notified_at IS NULL OR ip.last_notified_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        """)
        replenishments = cursor.fetchall()
        
        for item in replenishments:
            email = get_user_email(cursor, item['core_id'])
            if not email: continue

            subject = f"Time to reorder your {item['main_category'].replace('_', ' ').title()}?"
            message = f"Hi there! We noticed it's been about {item['lifetime_days']} days since you bought {item['brand'].title()} {item['main_category'].replace('_', ' ').title()}. Time to restock?"
            
            if send_sendgrid_email(email, subject, message):
                update_last_notified(cursor, db, item['profile_id'])
                notifications_sent += 1

        # RULE 2: High Interest / Spike Reminders
        cursor.execute("""
            SELECT 
                profile_id, core_id, main_category, brand, interest_score
            FROM interest_profiles
            WHERE interest_score >= 3.0
              AND suppress_until IS NULL
              AND (last_notified_at IS NULL OR last_notified_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        """)
        interests = cursor.fetchall()

        for item in interests:
            email = get_user_email(cursor, item['core_id'])
            if not email: continue

            subject = f"We saw you liked {item['brand'].title()} {item['main_category'].replace('_', ' ').title()}"
            message = f"Hi there! We noticed you've been checking out {item['brand'].title()} {item['main_category'].replace('_', ' ').title()} recently. It's a great choice!"
            
            if send_sendgrid_email(email, subject, message):
                update_last_notified(cursor, db, item['profile_id'])
                notifications_sent += 1

        logger.info(f"Notification engine finished. Total emails sent: {notifications_sent}")

    except Exception as e:
        logger.error(f"Error in Notification Engine: {e}")
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    run_engine()
