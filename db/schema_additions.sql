-- ============================================================
-- CPRP — Schema Additions (run AFTER db/schema.sql)
-- File: db/schema_additions.sql
-- Adds ONLY tables that do not exist yet:
--   engagement_patterns, identity_confidence, recommendation_log
-- ============================================================
USE cprp;

-- ── TABLE: engagement_patterns ────────────────────────────────
-- Stores per-user hourly engagement data for timing intelligence
-- Populated by the Kafka consumer on every event
CREATE TABLE IF NOT EXISTS engagement_patterns (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    core_id      VARCHAR(36) NOT NULL,
    hour_of_day  TINYINT NOT NULL,          -- 0-23
    day_of_week  TINYINT NOT NULL,          -- 0=Mon, 6=Sun
    event_count  INT DEFAULT 1,
    last_seen    DATETIME DEFAULT NOW(),
    updated_at   DATETIME DEFAULT NOW(),
    UNIQUE KEY unique_user_hour (core_id, hour_of_day, day_of_week),
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);

-- ── TABLE: identity_confidence ────────────────────────────────
-- Stores confidence score for each identity match
-- Higher score = more signals matched (email+phone+device = high)
CREATE TABLE IF NOT EXISTS identity_confidence (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    core_id          VARCHAR(36) NOT NULL,
    match_signals    VARCHAR(255) DEFAULT NULL,  -- e.g. "email,phone,device"
    confidence_score FLOAT DEFAULT 0.5,          -- 0.0 to 1.0
    resolution_type  VARCHAR(50) DEFAULT "deterministic", -- deterministic/probabilistic
    created_at       DATETIME DEFAULT NOW(),
    updated_at       DATETIME DEFAULT NOW(),
    UNIQUE KEY unique_core (core_id),
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);

-- ── TABLE: recommendation_log ─────────────────────────────────
-- Detailed log of every recommendation shown with outcome tracking
-- Powers CTR and conversion rate calculations
CREATE TABLE IF NOT EXISTS recommendation_log (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    core_id          VARCHAR(36) NOT NULL,
    main_category    VARCHAR(100) NOT NULL,
    brand            VARCHAR(100) DEFAULT "unknown",
    price_range      VARCHAR(50)  DEFAULT "unknown",
    epsilon_score    FLOAT DEFAULT 0.0,
    rank_position    INT DEFAULT 1,
    trigger_type     VARCHAR(50) DEFAULT "api",   -- api/timeline/interest
    outcome          VARCHAR(50) DEFAULT "shown", -- shown/clicked/purchased/ignored/dismissed
    shown_at         DATETIME DEFAULT NOW(),
    outcome_at       DATETIME DEFAULT NULL,
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);

-- ── Add dismiss_count to interest_profiles if missing ─────────
ALTER TABLE interest_profiles
    ADD COLUMN IF NOT EXISTS dismiss_count INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ignore_count  INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS wishlist_count INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS search_count  INT DEFAULT 0;

-- ── Add email + device columns to users if missing ────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS device_id   VARCHAR(255) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS platform    VARCHAR(50)  DEFAULT NULL,  -- web/mobile/crm
    ADD COLUMN IF NOT EXISTS last_active DATETIME     DEFAULT NULL;

-- ── Indexes for performance ───────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ip_score     ON interest_profiles(core_id, interest_score DESC);
CREATE INDEX IF NOT EXISTS idx_ip_suppress  ON interest_profiles(suppress_until);
CREATE INDEX IF NOT EXISTS idx_ep_hour      ON engagement_patterns(core_id, hour_of_day);
CREATE INDEX IF NOT EXISTS idx_rec_core     ON recommendation_log(core_id, shown_at DESC);
CREATE INDEX IF NOT EXISTS idx_int_coretime ON interactions(core_id, event_time DESC);

SELECT "Schema additions applied successfully" AS status;