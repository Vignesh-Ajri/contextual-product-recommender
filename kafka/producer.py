# ============================================================
# STEP 3 - Kafka Producer
# File: kafka/producer.py
#
# What this does:
# - Reads your cleaned CSV row by row
# - Sends each row as a JSON message to Kafka
# - Think of it as: "person dropping letters into a post box"
#
# Run AFTER consumer.py is running in another terminal.
# Command: python kafka/producer.py
#
# Kafka must be running before you run this.
# Start Kafka with: docker-compose up (Day 3 setup)
# OR manually start ZooKeeper + Kafka server
# ============================================================

import json          # json = converts Python dict to text format for sending
import time          # time = for adding small delays between messages
import pandas as pd  # pandas = for reading the CSV file
from kafka import KafkaProducer   # KafkaProducer = the tool that sends messages to Kafka

# ── 1. Configuration ──────────────────────────────────────────
KAFKA_SERVER = "localhost:9092"    # address where Kafka is running
TOPIC_NAME   = "user_events"       # name of the "post box" we're dropping into
CSV_FILE     = "data/2019-Oct-cleaned.csv"  # our cleaned Kaggle data
DELAY        = 0.1                 # seconds to wait between each message (0.1 = fast)


# ── 2. Connect to Kafka ───────────────────────────────────────
print("Connecting to Kafka...")

try:
    producer = KafkaProducer(
        bootstrap_servers = KAFKA_SERVER,           # where is Kafka running
        value_serializer  = lambda v: json.dumps(v).encode("utf-8")
        # value_serializer = converts our Python dict → JSON text → bytes
        # Kafka only sends bytes, not Python objects directly
    )
    print("✅ Connected to Kafka successfully")

except Exception as e:
    print(f"❌ Could not connect to Kafka: {e}")
    print("Make sure Kafka is running on localhost:9092")
    exit(1)   # stop the script if Kafka is not available


# ── 3. Load cleaned CSV ───────────────────────────────────────
print(f"\nLoading data from {CSV_FILE}...")

try:
    df = pd.read_csv(CSV_FILE)
    print(f"✅ Loaded {len(df)} rows")
except FileNotFoundError:
    print(f"❌ File not found: {CSV_FILE}")
    print("Run data/clean_data.py first!")
    exit(1)


# ── 4. Send each row as a Kafka message ───────────────────────
print(f"\nSending events to Kafka topic: '{TOPIC_NAME}'")
print("Press Ctrl+C to stop\n")

sent_count  = 0   # counter for successful sends
error_count = 0   # counter for failed sends

for index, row in df.iterrows():
    # Convert each row into a clean Python dictionary
    # This becomes the "letter" we drop into Kafka
    event = {
        "event_id":      int(row.get("event_id", index)),
        "user_id":       str(row.get("user_id", "unknown")),
        "event_type":    str(row.get("event_type", "view")),
        "main_category": str(row.get("main_category", "unknown")),
        "brand":         str(row.get("brand", "unknown")),
        "price_range":   str(row.get("price_range", "unknown")),
        "event_time":    str(row.get("event_time", "")),
        "source":        "kaggle"    # mark where this data came from
    }

    try:
        # Send the event to Kafka topic
        producer.send(TOPIC_NAME, value=event)
        sent_count += 1

        # Print progress every 100 messages
        if sent_count % 100 == 0:
            print(f"  Sent {sent_count} events...")

        # Small delay so we don't overwhelm the consumer
        time.sleep(DELAY)

    except Exception as e:
        error_count += 1
        print(f"  ❌ Error sending row {index}: {e}")


# ── 5. Flush and close ────────────────────────────────────────
# flush() = make sure all messages in buffer are actually sent
# before we close the connection
producer.flush()
producer.close()

print(f"\n── Done ─────────────────────────────")
print(f"✅ Successfully sent: {sent_count} events")
print(f"❌ Failed:            {error_count} events")
print(f"Topic: {TOPIC_NAME}")
