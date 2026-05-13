"""
CPRP — Daily Data Maintenance Script
Run daily via cron/Task Scheduler to enforce the
"Minimal, Recent, Useful" data storage strategy.

Usage:
    python scripts/cleanup.py              # Run cleanup
    python scripts/cleanup.py --dry-run    # Preview without deleting

Schedule (Linux cron):
    0 2 * * * cd /path/to/cprp && python scripts/cleanup.py >> logs/cleanup.log 2>&1

Schedule (Windows Task Scheduler):
    Action: python
    Arguments: scripts/cleanup.py
    Start in: D:\\PROJECT-MCA\\cprp
"""

import sys
import logging
import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("cleanup")

# ── Configuration ─────────────────────────────────────────────
INTERACTION_RETENTION_DAYS = 45     # Keep raw events for 45 days
NOTIFICATION_RETENTION_DAYS = 30   # Keep notification history for 30 days
SCORE_DECAY_FACTOR = 0.85          # Decay inactive scores by 15%
SCORE_DECAY_AFTER_DAYS = 15        # Start decay after 15 days of inactivity
DEAD_PROFILE_THRESHOLD = 0.1       # Remove profiles with score below this
DEAD_PROFILE_AGE_DAYS = 30         # Only remove if also older than this

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME",     "cprp")
}

DRY_RUN = "--dry-run" in sys.argv


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def run_cleanup():
    logger.info("=" * 55)
    logger.info("  CPRP — Daily Cleanup")
    logger.info(f"  Mode: {'DRY RUN (no changes)' if DRY_RUN else 'LIVE'}")
    logger.info(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 55)

    conn = get_db()
    cursor = conn.cursor()

    stats = {}

    # ── 1. Count before ──────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM interactions")
    stats["interactions_before"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM notifications")
    stats["notifications_before"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM interest_profiles")
    stats["profiles_before"] = cursor.fetchone()[0]

    # ── 2. Purge old interactions ─────────────────────────────
    cursor.execute(
        "SELECT COUNT(*) FROM interactions WHERE event_time < DATE_SUB(NOW(), INTERVAL %s DAY)",
        (INTERACTION_RETENTION_DAYS,)
    )
    stale_interactions = cursor.fetchone()[0]

    if not DRY_RUN and stale_interactions > 0:
        cursor.execute(
            "DELETE FROM interactions WHERE event_time < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (INTERACTION_RETENTION_DAYS,)
        )
    logger.info(f"Interactions expired: {stale_interactions}")

    # ── 3. Purge old notifications ────────────────────────────
    cursor.execute(
        "SELECT COUNT(*) FROM notifications WHERE sent_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
        (NOTIFICATION_RETENTION_DAYS,)
    )
    stale_notifications = cursor.fetchone()[0]

    if not DRY_RUN and stale_notifications > 0:
        cursor.execute(
            "DELETE FROM notifications WHERE sent_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (NOTIFICATION_RETENTION_DAYS,)
        )
    logger.info(f"Notifications expired: {stale_notifications}")

    # ── 4. Decay stale interest scores ────────────────────────
    cursor.execute(
        """SELECT COUNT(*) FROM interest_profiles
           WHERE updated_at < DATE_SUB(NOW(), INTERVAL %s DAY)
             AND interest_score > %s""",
        (SCORE_DECAY_AFTER_DAYS, DEAD_PROFILE_THRESHOLD)
    )
    decay_count = cursor.fetchone()[0]

    if not DRY_RUN and decay_count > 0:
        cursor.execute(
            """UPDATE interest_profiles
               SET interest_score   = interest_score   * %s,
                   browse_score     = browse_score     * %s,
                   engagement_score = engagement_score * %s
               WHERE updated_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                 AND interest_score > %s""",
            (SCORE_DECAY_FACTOR, SCORE_DECAY_FACTOR, SCORE_DECAY_FACTOR,
             SCORE_DECAY_AFTER_DAYS, DEAD_PROFILE_THRESHOLD)
        )
    logger.info(f"Profiles decayed (×{SCORE_DECAY_FACTOR}): {decay_count}")

    # ── 5. Remove dead profiles ───────────────────────────────
    cursor.execute(
        """SELECT COUNT(*) FROM interest_profiles
           WHERE interest_score < %s
             AND purchase_count = 0
             AND updated_at < DATE_SUB(NOW(), INTERVAL %s DAY)""",
        (DEAD_PROFILE_THRESHOLD, DEAD_PROFILE_AGE_DAYS)
    )
    dead_profiles = cursor.fetchone()[0]

    if not DRY_RUN and dead_profiles > 0:
        cursor.execute(
            """DELETE FROM interest_profiles
               WHERE interest_score < %s
                 AND purchase_count = 0
                 AND updated_at < DATE_SUB(NOW(), INTERVAL %s DAY)""",
            (DEAD_PROFILE_THRESHOLD, DEAD_PROFILE_AGE_DAYS)
        )
    logger.info(f"Dead profiles removed: {dead_profiles}")

    # ── 6. Commit & report ────────────────────────────────────
    if not DRY_RUN:
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM interactions")
    stats["interactions_after"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM interest_profiles")
    stats["profiles_after"] = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    logger.info("")
    logger.info("── Summary ──────────────────────────────────")
    logger.info(f"  Interactions: {stats['interactions_before']} → {stats['interactions_after']}")
    logger.info(f"  Profiles:     {stats['profiles_before']} → {stats['profiles_after']}")
    logger.info(f"  Freed:        {stale_interactions + dead_profiles} rows")
    if DRY_RUN:
        logger.info("  ⚠ DRY RUN — no changes were made")
    logger.info("── Done ─────────────────────────────────────")


if __name__ == "__main__":
    try:
        run_cleanup()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)
