"""
CPRP — Kafka Producer for FMCG Events
Reads from the synthetic FMCG data CSV and publishes to Kafka.

Usage:
    1. Generate data first:  python data/generate_fmcg_data.py
    2. Run producer:         python kafka/producer.py
    3. Run consumer:         python kafka/consumer.py
"""

import json
import time
import pandas as pd
import os
from dotenv import load_dotenv
from kafka import KafkaProducer
load_dotenv()

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME   = os.getenv("KAFKA_TOPIC_EVENTS", "user_events")
CSV_FILE     = "data/fmcg_events.csv"
DELAY        = 0.05  # 50ms between events (20 events/sec)

print("=" * 55)
print("  CPRP — FMCG Event Producer")
print("=" * 55)

print("\nConnecting to Kafka...")

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    print("Connected to Kafka successfully")

except Exception as e:
    print(f"Could not connect to Kafka: {e}")
    print("Make sure Kafka is running on localhost:9092")
    print("Run: docker-compose up -d")
    exit(1)

print(f"\nLoading data from {CSV_FILE}...")

try:
    df = pd.read_csv(CSV_FILE)
    print(f"Loaded {len(df)} rows")
except FileNotFoundError:
    print(f"File not found: {CSV_FILE}")
    print("Run 'python data/generate_fmcg_data.py' first!")
    exit(1)

# Show data summary
print(f"\nCategories: {df['main_category'].nunique()}")
print(f"Users:      {df['user_id'].nunique()}")
print(f"Brands:     {df['brand'].nunique()}")

print(f"\nSending events to Kafka topic: '{TOPIC_NAME}'")
print(f"Speed: {1/DELAY:.0f} events/sec")
print("Press Ctrl+C to stop\n")

sent_count  = 0
error_count = 0

for index, row in df.iterrows():
    event = {
        "event_id":       int(row.get("event_id", index)),
        "user_id":        str(row.get("user_id", "unknown")),
        "event_type":     str(row.get("event_type", "view")),
        "main_category":  str(row.get("main_category", "unknown")),
        "brand":          str(row.get("brand", "unknown")),
        "price_range":    str(row.get("price_range", "unknown")),
        "product_name":   str(row.get("product_name", "")),
        "search_query":   str(row.get("search_query", "")),
        "event_time":     str(row.get("event_time", "")),
        "source":         str(row.get("source", "synthetic")),
        "session_id":     str(row.get("session_id", "")),
        "age_group":      str(row.get("age_group", "")),
        "gender":         str(row.get("gender", "")),
        "city":           str(row.get("city", "")),
        "state":          str(row.get("state", "")),
        "country":        str(row.get("country", "India")),
        "device_type":    str(row.get("device_type", "")),
        "platform":       str(row.get("platform", "")),
    }

    # Clean up "nan" strings from pandas
    for key in event:
        if event[key] == "nan":
            event[key] = ""

    try:
        producer.send(TOPIC_NAME, value=event)
        sent_count += 1

        if sent_count % 500 == 0:
            print(f"  Sent {sent_count:,} / {len(df):,} events...")

        time.sleep(DELAY)

    except Exception as e:
        error_count += 1
        print(f"Error sending row {index}: {e}")

    except KeyboardInterrupt:
        print(f"\nStopped by user at row {index}")
        break

producer.flush()
producer.close()

print(f"\n── Done ─────────────────────────────────")
print(f"Successfully sent: {sent_count:,} events")
print(f"Failed:            {error_count:,} events")
print(f"Topic: {TOPIC_NAME}")