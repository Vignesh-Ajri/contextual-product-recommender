import json
import time
import pandas as pd
from kafka import KafkaProducer

KAFKA_SERVER = "localhost:9092"
TOPIC_NAME   = "user_events"
CSV_FILE     = "data/2019-Oct-cleaned.csv"
DELAY        = 0.1

print("Connecting to Kafka...")

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    print("Connected to Kafka successfully")

except Exception as e:
    print(f"Could not connect to Kafka: {e}")
    print("Make sure Kafka is running on localhost:9092")
    exit(1)

print(f"\nLoading data from {CSV_FILE}...")

try:
    df = pd.read_csv(CSV_FILE)
    print(f"Loaded {len(df)} rows")
except FileNotFoundError:
    print(f"File not found: {CSV_FILE}")
    print("Run data/clean_data.py first!")
    exit(1)

print(f"\nSending events to Kafka topic: '{TOPIC_NAME}'")
print("Press Ctrl+C to stop\n")

sent_count  = 0
error_count = 0

for index, row in df.iterrows():
    event = {
        "event_id":      int(row.get("event_id", index)),
        "user_id":       str(row.get("user_id", "unknown")),
        "event_type":    str(row.get("event_type", "view")),
        "main_category": str(row.get("main_category", "unknown")),
        "brand":         str(row.get("brand", "unknown")),
        "price_range":   str(row.get("price_range", "unknown")),
        "event_time":    str(row.get("event_time", "")),
        "source":        "kaggle"
    }

    try:
        producer.send(TOPIC_NAME, value=event)
        sent_count += 1

        if sent_count % 100 == 0:
            print(f"  Sent {sent_count} events...")

        time.sleep(DELAY)

    except Exception as e:
        error_count += 1
        print(f"Error sending row {index}: {e}")

producer.flush()
producer.close()

print(f"\n── Done ─────────────────────────────")
print(f"Successfully sent: {sent_count} events")
print(f"Failed:            {error_count} events")
print(f"Topic: {TOPIC_NAME}")