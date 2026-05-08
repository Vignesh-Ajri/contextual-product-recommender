import pandas as pd  
import os

RAW_FILE   = "data/2019-Oct.csv"
CLEAN_FILE = "data/2019-Oct-cleaned.csv"

print("Loading raw data...")
df = pd.read_csv(RAW_FILE, nrows=500000)

print(f"Raw data shape: {df.shape}")
print(f"Columns found: {list(df.columns)}")

KEEP_COLUMNS = [
    "user_id",
    "event_type",
    "category_code",
    "brand",
    "price",
    "event_time"
]

existing_columns = [col for col in KEEP_COLUMNS if col in df.columns]
df = df[existing_columns]

print(f"\nAfter column selection: {df.shape}")

before = len(df)
df = df.drop_duplicates()
after  = len(df)
print(f"Removed {before - after} duplicate rows")

df["brand"] = df["brand"].fillna("unknown")
df["category_code"] = df["category_code"].fillna("unknown")
df["price"] = df["price"].fillna(0)
df["event_time"] = df["event_time"].str.replace(" UTC", "", regex=False)

valid_events = ["view", "cart", "purchase"]
df = df[df["event_type"].isin(valid_events)]
print(f"After filtering event types: {df.shape}")

def price_to_range(price):
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

df["price_range"] = df["price"].apply(price_to_range)

df["main_category"] = df["category_code"].apply(
    lambda x: x.split(".")[0] if "." in str(x) else str(x)
)

df = df.reset_index(drop=True)
df["event_id"] = df.index + 1

df.to_csv(CLEAN_FILE, index=False)
print(f"\nCleaned data saved to: {CLEAN_FILE}")
print(f"Total clean rows: {len(df)}")
print(f"\nSample of cleaned data:")
print(df.head(5).to_string())

print(f"\n── Summary ──────────────────────────")
print(f"Event types: {df['event_type'].value_counts().to_dict()}")
print(f"Top 5 categories: {df['main_category'].value_counts().head(5).to_dict()}")
print(f"Top 5 brands: {df['brand'].value_counts().head(5).to_dict()}")
print(f"Price ranges: {df['price_range'].value_counts().to_dict()}")