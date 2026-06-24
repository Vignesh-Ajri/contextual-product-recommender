import pandas as pd
import numpy as np
import uuid
import os
import random

print("Generating synthetic Cross-Device Identity dataset...")
os.makedirs("data", exist_ok=True)

# Generate 50,000 realistic device/cookie events
num_events = 50000

# Base pool of true underlying users
num_true_users = 10000
true_users = [str(uuid.uuid4()) for _ in range(num_true_users)]

data = []
for i in range(num_events):
    true_user = random.choice(true_users)
    
    # Simulate identifiers a user might leave behind
    # Users have 1-3 devices (desktop, mobile, tablet)
    device_id = f"dev_{true_user[:8]}_{random.randint(1, 3)}" 
    
    # IP addresses rotate, maybe 1-5 IPs per user
    ip_addr = f"192.168.{random.randint(1,255)}.{int(true_user[0], 16) % 20}"
    
    # 30% of the time they are logged in (we see their email hash)
    email_hash = f"email_{true_user[:12]}" if random.random() < 0.3 else None
    
    # 10% of the time they use a loyalty card
    loyalty_id = f"loyalty_{true_user[-6:]}" if random.random() < 0.1 else None
    
    data.append({
        "event_id": f"evt_{i}",
        "true_user_id": true_user, # Ground truth (not available to model directly)
        "device_id": device_id,
        "ip_address": ip_addr,
        "email_hash": email_hash,
        "loyalty_id": loyalty_id,
        "timestamp": pd.Timestamp.now() - pd.Timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
    })

df = pd.DataFrame(data)
df.to_csv("data/synthetic_identity_events.csv", index=False)
print(f"Generated data/synthetic_identity_events.csv with {len(df)} events.")
print(f"Contains {num_true_users} unique true users.")
print(f"Contains {df['device_id'].nunique()} unique device IDs.")
