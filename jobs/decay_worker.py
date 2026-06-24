import os
import sys
import logging
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_CONFIG = {
    "host": os.getenv("DB_HOST","localhost"),
    "port": int(os.getenv("DB_PORT", 3307)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def run_decay():
    logger.info("Starting CPRP Passive Time Decay Worker")
    db = get_db()
    cursor = db.cursor()

    try:
        # Find profiles that haven't been updated in the last 24 hours
        # and decay their scores by 5% (multiply by 0.95)
        logger.info("Applying 5% decay to inactive profiles...")
        
        cursor.execute("""
            UPDATE interest_profiles
            SET interest_score = GREATEST(0, interest_score * 0.95),
                browse_score = GREATEST(0, browse_score * 0.95),
                purchase_score = GREATEST(0, purchase_score * 0.95),
                engagement_score = GREATEST(0, engagement_score * 0.95)
            WHERE updated_at < DATE_SUB(NOW(), INTERVAL 1 DAY)
              AND interest_score > 0
        """)
        
        db.commit()
        logger.info(f"Decay applied to {cursor.rowcount} dormant profiles successfully.")

    except Exception as e:
        logger.error(f"Error in Decay Worker: {e}")
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    run_decay()
