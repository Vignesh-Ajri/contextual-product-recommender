import os
import django
import sys
import mysql.connector
from datetime import datetime, timedelta
import random
import uuid
import requests
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Address
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))

User = get_user_model()

# Configuration
CPRP_API_URL = os.getenv('CPRP_API_URL', 'http://localhost:5000')

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3307)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "cprp"),
    "database": os.getenv("DB_NAME", "cprp"),
}

USERS_TO_CREATE = [
    {
        "email": "ssvignesh2003@gmail.com",
        "phone": "+919876543210",
        "city": "Bengaluru",
        "state": "Karnataka",
        "age_group": "18-24",
        "gender": "male",
        "persona": "oral_care", # Will view/buy mouthwash, toothpaste
    },
    {
        "email": "vigneshajri2003@gmail.com",
        "phone": "+919876543211",
        "city": "Mumbai",
        "state": "Maharashtra",
        "age_group": "25-34",
        "gender": "male",
        "persona": "cosmetics", # Will view/cart lipstick, foundation
    },
    {
        "email": "ssvigga2003@gmail.com",
        "phone": "+919876543212",
        "city": "Delhi",
        "state": "Delhi",
        "age_group": "18-24",
        "gender": "female",
        "persona": "hair_care", # Will view/dismiss shampoo
    },
    {
        "email": "demo03985@gmail.com",
        "phone": "+919876543213",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "age_group": "35-44",
        "gender": "female",
        "persona": "skin_care", # Will view/buy face_wash, moisturizer
    },
    {
        "email": "1ms24mc105@msrit.edu",
        "phone": "+919876543214",
        "city": "Bengaluru",
        "state": "Karnataka",
        "age_group": "18-24",
        "gender": "male",
        "persona": "household", # Random household goods
    }
]

def wipe_cprp_database():
    print("Connecting to CPRP MySQL database...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Disable foreign key checks temporarily
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        tables = ['interactions', 'interest_profiles', 'user_demographics', 'identities', 'users', 'notifications']
        for table in tables:
            print(f"Truncating {table}...")
            cursor.execute(f"TRUNCATE TABLE {table};")
            
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        cursor.close()
        conn.close()
        print("CPRP MySQL Database wiped successfully.")
    except Exception as e:
        print(f"Error wiping MySQL DB: {e}")
        sys.exit(1)

def wipe_django_database():
    print("Wiping Django non-superuser data...")
    User.objects.filter(is_superuser=False).delete()
    print("Django users wiped successfully.")

def create_users():
    print("Creating real users...")
    for u_data in USERS_TO_CREATE:
        username = u_data["email"].split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=u_data["email"],
            password="password123",
            phone=u_data["phone"]
        )
        # Create address
        Address.objects.create(
            user=user,
            full_name=username,
            phone=u_data["phone"],
            address_line_1="123 Main St",
            city=u_data["city"],
            state=u_data["state"],
            postal_code="560001",
            country="India",
            is_default=True
        )
        print(f"Created {user.email}")

def send_event_to_cprp(user, u_data, event_type, category, brand, price_range, product_name):
    # This simulates what analytics/views.py does
    cprp_payload = {
        "user_id": str(user.id),
        "event_type": event_type,
        "category": category,
        "main_category": category,
        "brand": brand,
        "price_range": price_range,
        "product_name": product_name,
        "search_query": "",
        "session_id": "seed_session_123",
        "device_type": "mobile" if "mobile" in u_data.get("persona", "") else "desktop",
        "platform": "web",
        "email": user.email,
        "age_group": u_data["age_group"],
        "gender": u_data["gender"],
        "city": u_data["city"],
        "state": u_data["state"],
        "country": "India",
    }
    
    url = f"{CPRP_API_URL}/event"
    try:
        response = requests.post(url, json=cprp_payload, timeout=5)
        if response.status_code in [200, 201]:
            print(f"[{user.email}] {event_type} -> {brand} {category} (Success)")
        else:
            print(f"[{user.email}] Failed to send event to CPRP: {response.text}")
    except Exception as e:
        print(f"[{user.email}] Error connecting to CPRP API: {e}")

def simulate_activity():
    print("Simulating user activity...")
    for u_data in USERS_TO_CREATE:
        user = User.objects.get(email=u_data["email"])
        
        if u_data["persona"] == "oral_care":
            send_event_to_cprp(user, u_data, "view", "mouthwash", "listerine", "500-1000", "Listerine Cool Mint 500ml")
            send_event_to_cprp(user, u_data, "cart", "mouthwash", "listerine", "500-1000", "Listerine Cool Mint 500ml")
            send_event_to_cprp(user, u_data, "purchase", "mouthwash", "listerine", "500-1000", "Listerine Cool Mint 500ml")
            send_event_to_cprp(user, u_data, "view", "toothpaste", "sensodyne", "100-250", "Sensodyne Repair")
            
        elif u_data["persona"] == "cosmetics":
            send_event_to_cprp(user, u_data, "view", "lipstick", "maybelline", "100-250", "Maybelline Matte")
            send_event_to_cprp(user, u_data, "view", "foundation", "lakme", "500-1000", "Lakme Absolute")
            send_event_to_cprp(user, u_data, "cart", "lipstick", "maybelline", "100-250", "Maybelline Matte")
            # No purchase (Abandoned cart scenario)
            
        elif u_data["persona"] == "hair_care":
            send_event_to_cprp(user, u_data, "view", "shampoo", "dove", "500-1000", "Dove Hair Therapy")
            send_event_to_cprp(user, u_data, "view", "shampoo", "loreal", "500-1000", "Loreal Total Repair")
            send_event_to_cprp(user, u_data, "dismiss", "shampoo", "dove", "500-1000", "Dove Hair Therapy")
            
        elif u_data["persona"] == "skin_care":
            send_event_to_cprp(user, u_data, "search", "face_wash", "unknown", "unknown", "")
            send_event_to_cprp(user, u_data, "view", "face_wash", "himalaya", "50-100", "Himalaya Neem")
            send_event_to_cprp(user, u_data, "purchase", "face_wash", "himalaya", "50-100", "Himalaya Neem")
            send_event_to_cprp(user, u_data, "view", "moisturizer", "nivea", "500-1000", "Nivea Soft")
            
        elif u_data["persona"] == "household":
            send_event_to_cprp(user, u_data, "view", "detergent", "ariel", "500-1000", "Ariel Matic")
            send_event_to_cprp(user, u_data, "view", "dishwash", "vim", "250-500", "Vim Liquid")
            
        time.sleep(0.5) # Slight delay between users

if __name__ == "__main__":
    print("=== CPRP Real User Seeding Script ===")
    wipe_cprp_database()
    wipe_django_database()
    create_users()
    simulate_activity()
    print("=== Seeding Complete ===")
