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
    last_notified_at  DATETIME     DEFAULT NULL,

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
    ('toothpaste',      10,   'Toothpaste tube — ~10 days'),
    ('toothbrush',      15,   'Toothbrush — replace every 15 days'),
    ('mouthwash',       10,   'Mouthwash bottle — ~10 days'),

    -- Hair Care
    ('shampoo',         15,   'Shampoo bottle — ~15 days'),
    ('conditioner',     15,   'Conditioner — ~15 days'),
    ('hair_oil',        15,   'Hair oil bottle — ~15 days'),
    ('hair_color',      10,   'Hair color — 10 days'),

    -- Skin Care
    ('face_wash',       10,   'Face wash tube — ~10 days'),
    ('moisturizer',     15,   'Moisturizer jar — ~15 days'),
    ('sunscreen',       10,   'Sunscreen — ~10 days'),
    ('face_cream',      15,   'Face cream — ~15 days'),
    ('body_lotion',     15,   'Body lotion — ~15 days'),
    ('lip_balm',        10,   'Lip balm — ~10 days'),

    -- Cosmetics
    ('lipstick',        15,   'Lipstick — ~15 days'),
    ('foundation',      15,   'Foundation — ~15 days'),
    ('mascara',         15,   'Mascara — ~15 days'),
    ('eyeliner',        15,   'Eyeliner — ~15 days'),
    ('nail_polish',     15,   'Nail polish — ~15 days'),
    ('compact_powder',  15,   'Compact powder — ~15 days'),

    -- Personal Care
    ('soap',            10,   'Soap bar/body wash — ~10 days'),
    ('deodorant',       15,   'Deodorant — ~15 days'),
    ('perfume',         15,   'Perfume bottle — ~15 days'),
    ('razor',           5,    'Disposable razor — ~5 days'),
    ('shaving_cream',   15,   'Shaving cream — ~15 days'),
    ('hand_sanitizer',  10,   'Hand sanitizer — ~10 days'),

    -- Household Essentials
    ('detergent',       15,   'Laundry detergent — ~15 days'),
    ('dishwash',        10,   'Dishwash liquid — ~10 days'),
    ('floor_cleaner',   15,   'Floor cleaner — ~15 days'),
    ('tissue_paper',    5,    'Tissue paper pack — ~5 days'),
    ('toilet_cleaner',  15,   'Toilet cleaner — ~15 days'),
    ('air_freshener',   15,   'Air freshener — ~15 days'),

    -- Fallback
    ('unknown',         15,   'Default fallback — 15 days');

-- ═══════════════════════════════════════════════════════════════
-- MIGRATION: Add new indexes if tables already exist
-- ═══════════════════════════════════════════════════════════════

-- ALTER TABLE interest_profiles
--     ADD COLUMN IF NOT EXISTS browse_score     FLOAT DEFAULT 0.0,
--     ADD COLUMN IF NOT EXISTS purchase_score   FLOAT DEFAULT 0.0,
--     ADD COLUMN IF NOT EXISTS engagement_score FLOAT DEFAULT 0.0,
--     ADD COLUMN IF NOT EXISTS cart_count       INT   DEFAULT 0,
--     ADD COLUMN IF NOT EXISTS dismiss_count    INT   DEFAULT 0,
--     ADD COLUMN IF NOT EXISTS total_spent      FLOAT DEFAULT 0.0,
--     ADD COLUMN IF NOT EXISTS last_notified_at DATETIME DEFAULT NULL;

-- ALTER TABLE interactions
--     ADD COLUMN IF NOT EXISTS product_name  VARCHAR(255) DEFAULT NULL,
--     ADD COLUMN IF NOT EXISTS search_query  VARCHAR(255) DEFAULT NULL,
--     ADD COLUMN IF NOT EXISTS session_id    VARCHAR(100) DEFAULT NULL,
--     ADD COLUMN IF NOT EXISTS device_type   VARCHAR(50)  DEFAULT NULL;

SHOW TABLES;