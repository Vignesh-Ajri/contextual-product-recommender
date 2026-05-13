-- ═══════════════════════════════════════════════════════════════
-- CPRP — Daily Cleanup Job
-- Run this daily via cron or scheduled task
-- Implements "Minimal, Recent, Useful" data strategy
-- ═══════════════════════════════════════════════════════════════

-- ─── 1. Purge interactions older than 45 days ────────────────
-- Raw events are only needed for recent analysis.
-- Interest profiles already capture the aggregated scores.
DELETE FROM interactions
WHERE event_time < DATE_SUB(NOW(), INTERVAL 45 DAY);

-- ─── 2. Purge old notifications (30 days) ────────────────────
-- Notification history is only needed for dedup checks.
DELETE FROM notifications
WHERE sent_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- ─── 3. Decay interest scores for inactive profiles ──────────
-- If a user hasn't interacted with a category in 15+ days,
-- their scores decay by 15% each run. This ensures stale
-- interests naturally lose priority over time.
UPDATE interest_profiles
SET interest_score   = interest_score   * 0.85,
    browse_score     = browse_score     * 0.85,
    engagement_score = engagement_score * 0.85
WHERE updated_at < DATE_SUB(NOW(), INTERVAL 15 DAY)
  AND interest_score > 0.1;

-- ─── 4. Remove dead profiles ─────────────────────────────────
-- Profiles with negligible scores and no purchases are noise.
-- Remove them to keep the table lean.
DELETE FROM interest_profiles
WHERE interest_score < 0.1
  AND purchase_count = 0
  AND updated_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- ─── 5. Summary report ──────────────────────────────────────
SELECT 'CLEANUP COMPLETE' AS status, NOW() AS run_time;

SELECT
    (SELECT COUNT(*) FROM interactions) AS remaining_interactions,
    (SELECT COUNT(*) FROM notifications) AS remaining_notifications,
    (SELECT COUNT(*) FROM interest_profiles) AS remaining_profiles,
    (SELECT COUNT(*) FROM users) AS total_users;
