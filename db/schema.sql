CREATE DATABASE IF NOT EXISTS cprp;
USE cprp;

-- ═══════════════════════════════════════════════════════════════
-- TIER 1: PERMANENT TABLES (Never Expires)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users (
    core_id       VARCHAR(36)  PRIMARY KEY,
    email         VARCHAR(255) DEFAULT NULL,
    phone         VARCHAR(20)  DEFAULT NULL,
    created_at    DATETIME     DEFAULT NOW(),
    updated_at    DATETIME     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS identities (
    id               INT          AUTO_INCREMENT PRIMARY KEY,
    core_id          VARCHAR(36)  NOT NULL,
    identifier_type  VARCHAR(50)  NOT NULL,
    identifier_value VARCHAR(255) NOT NULL,
    created_at       DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id),
    INDEX idx_identities_lookup (identifier_type, identifier_value)
);


CREATE TABLE IF NOT EXISTS user_demographics (
    demo_id       INT          AUTO_INCREMENT PRIMARY KEY,
    core_id       VARCHAR(36)  NOT NULL UNIQUE,
    age_group     VARCHAR(20)  DEFAULT NULL,
    gender        VARCHAR(20)  DEFAULT NULL,
    city          VARCHAR(100) DEFAULT NULL,
    state         VARCHAR(100) DEFAULT NULL,
    country       VARCHAR(50)  DEFAULT 'India',
    device_type   VARCHAR(50)  DEFAULT NULL,
    platform      VARCHAR(50)  DEFAULT NULL,
    language      VARCHAR(20)  DEFAULT NULL,
    updated_at    DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);

-- ═══════════════════════════════════════════════════════════════
-- TIER 2: ROLLING WINDOW TABLES (45-day TTL via cleanup job)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id  INT          AUTO_INCREMENT PRIMARY KEY,
    core_id         VARCHAR(36)  NOT NULL,
    event_type      VARCHAR(50)  NOT NULL,
    main_category   VARCHAR(100) DEFAULT NULL,
    brand           VARCHAR(100) DEFAULT NULL,
    price_range     VARCHAR(50)  DEFAULT NULL,
    product_name    VARCHAR(255) DEFAULT NULL, 
    search_query    VARCHAR(255) DEFAULT NULL,
    session_id      VARCHAR(100) DEFAULT NULL,
    device_type     VARCHAR(50)  DEFAULT NULL,
    event_time      DATETIME     DEFAULT NOW(),
    source          VARCHAR(100) DEFAULT 'api',
    FOREIGN KEY (core_id) REFERENCES users(core_id),
    INDEX idx_interactions_time (event_time),
    INDEX idx_interactions_user (core_id, event_time)
);

-- ═══════════════════════════════════════════════════════════════
-- TIER 3: CONTINUOUSLY UPDATED (Scores decay, values refresh)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS interest_profiles (
    profile_id        INT          AUTO_INCREMENT PRIMARY KEY,
    core_id           VARCHAR(36)  NOT NULL,
    main_category     VARCHAR(100) NOT NULL,
    brand             VARCHAR(100) DEFAULT 'unknown',
    price_range       VARCHAR(50)  DEFAULT 'unknown',

    interest_score    FLOAT        DEFAULT 1.0,
    browse_score      FLOAT        DEFAULT 0.0,
    purchase_score    FLOAT        DEFAULT 0.0,
    engagement_score  FLOAT        DEFAULT 0.0,
    browse_count      INT          DEFAULT 0,
    cart_count        INT          DEFAULT 0,
    purchase_count    INT          DEFAULT 0,
    dismiss_count     INT          DEFAULT 0,

    last_purchased    DATETIME     DEFAULT NULL,
    total_spent       FLOAT        DEFAULT 0.0,

    suppress_until    DATETIME     DEFAULT NULL,

    updated_at        DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id),
    UNIQUE KEY unique_user_cat_brand (core_id, main_category, brand),
    INDEX idx_profiles_score (interest_score DESC),
    INDEX idx_profiles_updated (updated_at)
);

-- ═══════════════════════════════════════════════════════════════
-- REFERENCE TABLES
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS products (
    product_id      INT          AUTO_INCREMENT PRIMARY KEY,
    product_name    VARCHAR(255) DEFAULT NULL,
    main_category   VARCHAR(100) NOT NULL,
    brand           VARCHAR(100) DEFAULT 'unknown',
    price_range     VARCHAR(50)  DEFAULT 'unknown',
    lifetime_days   INT          DEFAULT 365,
    created_at      DATETIME     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT          AUTO_INCREMENT PRIMARY KEY,
    core_id         VARCHAR(36)  NOT NULL,
    channel         VARCHAR(50)  DEFAULT 'email',
    message         TEXT         DEFAULT NULL,
    product_ids     TEXT         DEFAULT NULL,
    status          VARCHAR(50)  DEFAULT 'sent',
    sent_at         DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id),
    INDEX idx_notifications_time (sent_at)
);

CREATE TABLE IF NOT EXISTS product_lifetime (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    main_category   VARCHAR(100) UNIQUE NOT NULL,
    lifetime_days   INT          NOT NULL,
    description     VARCHAR(255) DEFAULT NULL
);

-- ═══════════════════════════════════════════════════════════════
-- FMCG / Personal Care Product Lifetimes
-- ═══════════════════════════════════════════════════════════════

INSERT IGNORE INTO product_lifetime (main_category, lifetime_days, description) VALUES
    -- Oral Care
    ('toothpaste',      30,   'Toothpaste tube — ~1 month'),
    ('toothbrush',      90,   'Toothbrush — replace every 3 months'),
    ('mouthwash',       30,   'Mouthwash bottle — ~1 month'),

    -- Hair Care
    ('shampoo',         45,   'Shampoo bottle — ~45 days'),
    ('conditioner',     60,   'Conditioner — ~2 months'),
    ('hair_oil',        45,   'Hair oil bottle — ~45 days'),
    ('hair_color',      30,   'Hair color — monthly touch-up'),

    -- Skin Care
    ('face_wash',       45,   'Face wash tube — ~45 days'),
    ('moisturizer',     60,   'Moisturizer jar — ~2 months'),
    ('sunscreen',       45,   'Sunscreen — ~45 days with daily use'),
    ('face_cream',      60,   'Face cream — ~2 months'),
    ('body_lotion',     45,   'Body lotion — ~45 days'),
    ('lip_balm',        30,   'Lip balm — ~1 month'),

    -- Cosmetics
    ('lipstick',        120,  'Lipstick — ~4 months'),
    ('foundation',      90,   'Foundation — ~3 months'),
    ('mascara',         90,   'Mascara — ~3 months (replace for hygiene)'),
    ('eyeliner',        90,   'Eyeliner — ~3 months'),
    ('nail_polish',     120,  'Nail polish — ~4 months'),
    ('compact_powder',  90,   'Compact powder — ~3 months'),

    -- Personal Care
    ('soap',            30,   'Soap bar/body wash — ~1 month'),
    ('deodorant',       30,   'Deodorant — ~1 month'),
    ('perfume',         180,  'Perfume bottle — ~6 months'),
    ('razor',           14,   'Disposable razor — ~2 weeks'),
    ('shaving_cream',   60,   'Shaving cream — ~2 months'),
    ('hand_sanitizer',  30,   'Hand sanitizer — ~1 month'),

    -- Household Essentials
    ('detergent',       30,   'Laundry detergent — ~1 month'),
    ('dishwash',        30,   'Dishwash liquid — ~1 month'),
    ('floor_cleaner',   45,   'Floor cleaner — ~45 days'),
    ('tissue_paper',    14,   'Tissue paper pack — ~2 weeks'),
    ('toilet_cleaner',  30,   'Toilet cleaner — ~1 month'),
    ('air_freshener',   30,   'Air freshener — ~1 month'),

    -- Fallback
    ('unknown',         45,   'Default fallback — 45 days');

-- ═══════════════════════════════════════════════════════════════
-- MIGRATION: Add new indexes if tables already exist
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE interest_profiles
    ADD COLUMN IF NOT EXISTS browse_score     FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS purchase_score   FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS engagement_score FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS cart_count       INT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS dismiss_count    INT   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_spent      FLOAT DEFAULT 0.0;

ALTER TABLE interactions
    ADD COLUMN IF NOT EXISTS product_name  VARCHAR(255) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS search_query  VARCHAR(255) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS session_id    VARCHAR(100) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS device_type   VARCHAR(50)  DEFAULT NULL;

SHOW TABLES;