import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3307)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "cprp"),
    "database": os.getenv("DB_NAME", "cprp")
}

print("Connecting to MySQL...")
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Ensure users exist before adding confidence (foreign key constraint)
    print("Loading data/identity_confidence.csv...")
    df = pd.read_csv("data/identity_confidence.csv")
    
    print("Inserting into users table...")
    # Insert new core_ids into users table to satisfy foreign keys
    for _, row in df.iterrows():
        cursor.execute("INSERT IGNORE INTO users (core_id) VALUES (%s)", (row['core_id'],))
        
    print("Inserting into identity_confidence table...")
    # Insert into identity_confidence
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO identity_confidence 
            (core_id, match_signals, confidence_score, resolution_type) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            match_signals=VALUES(match_signals), 
            confidence_score=VALUES(confidence_score),
            resolution_type=VALUES(resolution_type),
            updated_at=NOW()
        """, (row['core_id'], row['match_signals'], row['confidence_score'], row['resolution_type']))
        
    conn.commit()
    print(f"Successfully loaded {len(df)} identity records into DB.")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
