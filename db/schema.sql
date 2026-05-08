CREATE DATABASE IF NOT EXISTS cprp;
USE cprp;

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
    FOREIGN KEY (core_id) REFERENCES users(core_id)
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
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);

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
    UNIQUE KEY unique_user_cat_brand (core_id, main_category, brand)
);

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
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);

CREATE TABLE IF NOT EXISTS product_lifetime (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    main_category   VARCHAR(100) UNIQUE NOT NULL,
    lifetime_days   INT          NOT NULL,
    description     VARCHAR(255) DEFAULT NULL
);

INSERT IGNORE INTO product_lifetime (main_category, lifetime_days, description) VALUES
    ('stationery',   5,    'Pens, pencils — run out fast'),
    ('electronics',  1095, 'Mobiles, laptops — 3 years'),
    ('books',        180,  'Reference books — 6 months'),
    ('clothing',     365,  'Clothes — 1 year'),
    ('food',         7,    'Food items — 1 week'),
    ('furniture',    1825, 'Furniture — 5 years'),
    ('unknown',      90,   'Default fallback — 3 months');

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