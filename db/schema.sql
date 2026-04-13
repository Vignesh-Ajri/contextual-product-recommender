-- ============================================================
-- STEP 2 - Database Setup
-- File: db/schema.sql
--
-- What this does:
-- - Creates your database called "cprp"
-- - Creates 5 tables from your ER diagram (Fig 4.6 in report)
-- - Each table matches exactly what you designed
--
-- How to run:
-- Open MySQL and run: source db/schema.sql
-- OR paste this entire file into MySQL Workbench and execute
-- ============================================================


-- Create the database
CREATE DATABASE IF NOT EXISTS cprp;

-- Use this database for all tables below
USE cprp;


-- ── TABLE 1: users ───────────────────────────────────────────
-- Stores one row per unique person
-- This is the master identity record

CREATE TABLE IF NOT EXISTS users (
    core_id       VARCHAR(36)  PRIMARY KEY,   -- UUID like "a1b2c3d4-..." unique per person
    email         VARCHAR(255) DEFAULT NULL,  -- their email if known
    phone         VARCHAR(20)  DEFAULT NULL,  -- their phone if known
    created_at    DATETIME     DEFAULT NOW(), -- when profile was first created
    updated_at    DATETIME     DEFAULT NOW()  -- when profile was last updated
);


-- ── TABLE 2: identities ──────────────────────────────────────
-- Links different identifiers to one core_id
-- Example: cookie "abc123" and email "vignesh@gmail.com"
-- both belong to the same person → same core_id

CREATE TABLE IF NOT EXISTS identities (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    core_id         VARCHAR(36)  NOT NULL,                   -- links to users table
    identifier_type VARCHAR(50)  NOT NULL,                   -- "email", "cookie", "phone", "user_id"
    identifier_value VARCHAR(255) NOT NULL,                  -- the actual value
    created_at      DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id)          -- must exist in users table
);


-- ── TABLE 3: products ────────────────────────────────────────
-- Stores product info from Kaggle dataset
-- Your recommendation engine uses this to find similar products

CREATE TABLE IF NOT EXISTS products (
    product_id      INT          AUTO_INCREMENT PRIMARY KEY,
    product_name    VARCHAR(255) DEFAULT NULL,               -- name of product
    main_category   VARCHAR(100) NOT NULL,                   -- electronics, stationery etc
    brand           VARCHAR(100) DEFAULT "unknown",          -- samsung, apple etc
    price_range     VARCHAR(50)  DEFAULT "unknown",          -- 50k-70k, 0-500 etc
    lifetime_days   INT          DEFAULT 365,                -- how long product lasts
    created_at      DATETIME     DEFAULT NOW()
);


-- ── TABLE 4: interactions ────────────────────────────────────
-- Every event (view / cart / purchase) gets one row here
-- This is fed by your Kafka consumer in real time

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id  INT          AUTO_INCREMENT PRIMARY KEY,
    core_id         VARCHAR(36)  NOT NULL,                   -- who did the action
    product_id      INT          DEFAULT NULL,               -- which product
    event_type      VARCHAR(50)  NOT NULL,                   -- view / cart / purchase
    main_category   VARCHAR(100) DEFAULT NULL,               -- category of product
    brand           VARCHAR(100) DEFAULT NULL,               -- brand
    price_range     VARCHAR(50)  DEFAULT NULL,               -- price range
    event_time      DATETIME     DEFAULT NOW(),              -- when it happened
    source          VARCHAR(100) DEFAULT "kaggle",           -- where data came from
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);


-- ── TABLE 5: interest_profiles ───────────────────────────────
-- Stores how much a user is interested in each category
-- Score goes up when they view/buy, down when they ignore
-- This is the "4 parameters" from your Epsilon model

CREATE TABLE IF NOT EXISTS interest_profiles (
    profile_id      INT          AUTO_INCREMENT PRIMARY KEY,
    core_id         VARCHAR(36)  NOT NULL,                   -- which user
    main_category   VARCHAR(100) NOT NULL,                   -- which category
    brand           VARCHAR(100) DEFAULT "unknown",          -- preferred brand
    price_range     VARCHAR(50)  DEFAULT "unknown",          -- preferred price range
    interest_score  FLOAT        DEFAULT 1.0,                -- higher = more interested
    browse_count    INT          DEFAULT 0,                  -- how many times viewed
    purchase_count  INT          DEFAULT 0,                  -- how many times bought
    last_purchased  DATETIME     DEFAULT NULL,               -- last purchase date
    suppress_until  DATETIME     DEFAULT NULL,               -- don't recommend until this date
    updated_at      DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id),
    UNIQUE KEY unique_user_category (core_id, main_category, brand) -- one row per user+category+brand
);


-- ── TABLE 6: notifications ───────────────────────────────────
-- Logs every notification sent to every user
-- Useful for admin monitoring and avoiding repeat sends

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT          AUTO_INCREMENT PRIMARY KEY,
    core_id         VARCHAR(36)  NOT NULL,                   -- who received it
    channel         VARCHAR(50)  DEFAULT "email",            -- email / sms / push
    message         TEXT         DEFAULT NULL,               -- what was sent
    product_ids     TEXT         DEFAULT NULL,               -- which products were recommended
    status          VARCHAR(50)  DEFAULT "sent",             -- sent / failed / opened
    sent_at         DATETIME     DEFAULT NOW(),
    FOREIGN KEY (core_id) REFERENCES users(core_id)
);


-- ── TABLE 7: product_lifetime ────────────────────────────────
-- Admin can update these values (your simple "dashboard")
-- This is what drives the timeline-based notifications

CREATE TABLE IF NOT EXISTS product_lifetime (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    main_category   VARCHAR(100) UNIQUE NOT NULL,            -- category name
    lifetime_days   INT          NOT NULL,                   -- how many days product lasts
    description     VARCHAR(255) DEFAULT NULL                -- notes for admin
);

-- Insert default lifetimes for common categories
-- Admin can UPDATE these rows anytime (your "dashboard" feature)
INSERT IGNORE INTO product_lifetime (main_category, lifetime_days, description) VALUES
    ("stationery",   5,    "Pens, pencils — run out fast"),
    ("electronics",  1095, "Mobiles, laptops — 3 years"),
    ("books",        180,  "Reference books — 6 months"),
    ("clothing",     365,  "Clothes — 1 year"),
    ("food",         7,    "Food items — 1 week"),
    ("furniture",    1825, "Furniture — 5 years"),
    ("unknown",      90,   "Default fallback — 3 months");


-- Confirm everything was created
SHOW TABLES;
