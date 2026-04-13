# ============================================================
# STEP 1 - Data Cleaning
# File: data/clean_data.py
#
# What this does:
# - Reads the raw Kaggle CSV file
# - Keeps only the 5 columns we need
# - Removes duplicate rows
# - Fills missing values
# - Converts price into price range buckets (like "50k-70k")
# - Saves a clean version ready for Kafka
#
# Run this FIRST before anything else.
# Command: python data/clean_data.py
# ============================================================

import pandas as pd   # pandas = tool for reading and cleaning data
import os             # os = tool for file/folder operations

# ── 1. Load raw CSV ──────────────────────────────────────────
# Make sure you placed your Kaggle CSV inside the data/ folder
# and renamed it to raw_kaggle.csv

RAW_FILE   = "data/2019-Oct.csv"               # input  - your downloaded Kaggle file
CLEAN_FILE = "data/2019-Oct-cleaned.csv"       # output - what we save after cleaning

print("Loading raw data...")
df = pd.read_csv(RAW_FILE, nrows=500000) # read the CSV into a DataFrame (like an Excel sheet in Python)

print(f"Raw data shape: {df.shape}")  # prints how many rows and columns
print(f"Columns found: {list(df.columns)}")


# ── 2. Keep only the columns we need ─────────────────────────
# The Kaggle dataset has many columns.
# We only need these 5 for our project.

KEEP_COLUMNS = [
    "user_id",        # who is the user
    "event_type",     # what they did: view / cart / purchase
    "category_code",  # what product category: electronics, stationery etc
    "brand",          # brand of the product: samsung, apple etc
    "price",          # price of the product in original currency
    "event_time"      # when did this happen
]

# Only keep columns that actually exist in the file
# (some Kaggle files may have slightly different column names)
existing_columns = [col for col in KEEP_COLUMNS if col in df.columns]
df = df[existing_columns]

print(f"\nAfter column selection: {df.shape}")


# ── 3. Remove duplicate rows ──────────────────────────────────
# Sometimes the same event is recorded twice — we drop those

before = len(df)
df = df.drop_duplicates()             # removes exact duplicate rows
after  = len(df)
print(f"Removed {before - after} duplicate rows")


# ── 4. Fill missing (empty) values ───────────────────────────
# Some rows may have empty brand or category — we fill them
# with the word "unknown" so nothing breaks later

df["brand"]         = df["brand"].fillna("unknown")
df["category_code"] = df["category_code"].fillna("unknown")
df["price"]         = df["price"].fillna(0)          # if price missing, set 0
df["event_time"]    = df["event_time"].str.replace(" UTC", "", regex=False)

# ── 5. Keep only rows with known event types ──────────────────
# We only care about: view, cart, purchase
# Anything else is noise — remove it

valid_events = ["view", "cart", "purchase"]
df = df[df["event_type"].isin(valid_events)]
print(f"After filtering event types: {df.shape}")


# ── 6. Convert price to price range bucket ────────────────────
# Instead of storing exact price (₹65,432), we store a range
# This is your "price range" parameter from Epsilon model

def price_to_range(price):
    """Convert a raw price number into a readable range string."""
    if price <= 0:
        return "unknown"
    elif price < 500:
        return "0-500"
    elif price < 1000:
        return "500-1k"
    elif price < 5000:
        return "1k-5k"
    elif price < 10000:
        return "5k-10k"
    elif price < 30000:
        return "10k-30k"
    elif price < 70000:
        return "30k-70k"
    else:
        return "70k+"

# Apply the function to every row in the price column
df["price_range"] = df["price"].apply(price_to_range)


# ── 7. Clean up category names ────────────────────────────────
# category_code looks like "electronics.smartphone"
# We extract just the main category: "electronics"

df["main_category"] = df["category_code"].apply(
    lambda x: x.split(".")[0] if "." in str(x) else str(x)
)


# ── 8. Add a unique row ID ────────────────────────────────────
# Each event needs a unique ID for tracking
df = df.reset_index(drop=True)
df["event_id"] = df.index + 1        # simple 1, 2, 3... numbering


# ── 9. Save cleaned data ──────────────────────────────────────
df.to_csv(CLEAN_FILE, index=False)   # save to CSV without row numbers
print(f"\n✅ Cleaned data saved to: {CLEAN_FILE}")
print(f"Total clean rows: {len(df)}")
print(f"\nSample of cleaned data:")
print(df.head(5).to_string())        # show first 5 rows as preview


# ── 10. Quick summary ─────────────────────────────────────────
print(f"\n── Summary ──────────────────────────")
print(f"Event types: {df['event_type'].value_counts().to_dict()}")
print(f"Top 5 categories: {df['main_category'].value_counts().head(5).to_dict()}")
print(f"Top 5 brands: {df['brand'].value_counts().head(5).to_dict()}")
print(f"Price ranges: {df['price_range'].value_counts().to_dict()}")
