import re
import pandas as pd
import joblib
import uuid
import mysql.connector
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity
)
from flask_swagger_ui import get_swaggerui_blueprint
import os
from dotenv import load_dotenv
load_dotenv()

# Input validation constants
MAX_FIELD_LENGTH = 200
ALLOWED_EVENT_TYPES = {"view", "cart", "purchase"}

# Simple rate limiter: {ip: [timestamps]}
_rate_limit_store = defaultdict(list)
RATE_LIMIT_MAX = 60
RATE_LIMIT_WINDOW = 60

def check_rate_limit(ip):
    """Return True if rate limit exceeded."""
    now = datetime.now().timestamp()
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return True
    _rate_limit_store[ip].append(now)
    return False

def sanitize_string(value, max_len=MAX_FIELD_LENGTH):
    """Sanitize input: strip, truncate, remove control chars."""
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()[:max_len]
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)
    return value

app = Flask(__name__)

# Secret key for JWT tokens
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

def get_db():
    """Get a MySQL database connection."""
    return mysql.connector.connect(**DB_CONFIG)

print("Loading ML model...")
try:
    import numpy as np
    tfidf             = joblib.load("ml/tfidf.pkl")
    similarity_matrix = joblib.load("ml/cosine_sim.pkl")
    products_df       = pd.read_csv("ml/products.csv")
    collab_data       = joblib.load("ml/collab.pkl")
    model_data        = True

    print(f"Hybrid model loaded — {len(products_df)} products")
except FileNotFoundError:
    print("Model not found. Run ml/hybrid_model.py first!")
    print("API will start but /recommend endpoint won't work until model is trained")
    model_data = None


def resolve_identity(cursor, identifier, id_type="user_id"):
    """
    Find or create a core_id for the given identifier.
    Same logic as consumer.py — reused here for the API.
    """
    cursor.execute(
        "SELECT core_id FROM identities WHERE identifier_type=%s AND identifier_value=%s",
        (id_type, str(identifier))
    )
    result = cursor.fetchone()

    if result:
        return result[0]

    new_core_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO users (core_id) VALUES (%s)", (new_core_id,))
    cursor.execute(
        "INSERT INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,%s,%s)",
        (new_core_id, id_type, str(identifier))
    )
    return new_core_id


def get_lifetime(cursor, category):
    """Get suppression days for a product category."""
    cursor.execute(
        "SELECT lifetime_days FROM product_lifetime WHERE main_category=%s",
        (category,)
    )
    result = cursor.fetchone()
    return result[0] if result else 90

def find_similar_products(category, brand, price_range, top_n=5):
    '''
    Hybrid recommendation:
    50% Content-Based (TF-IDF cosine similarity)
    50% Collaborative Filtering (item-item similarity)
    '''
    if model_data is None:
        return []
 
    content_scores = np.zeros(len(products_df))
 
    match = products_df[
        (products_df["main_category"] == category) &
        (products_df["brand"]         == brand)
    ]
    if len(match) == 0:
        match = products_df[products_df["main_category"] == category]
 
    if len(match) > 0:
        idx = match.index[0]
        content_scores = similarity_matrix[idx]
 
    collab_scores = np.zeros(len(products_df))
    item_key      = f"{category}_{brand}"
 
    if item_key in collab_data["item_keys"]:
        item_idx   = collab_data["item_enc"].transform([item_key])[0]
        raw_collab = collab_data["item_sim_matrix"][item_idx]
 
        for i, prod in products_df.iterrows():
            pk = f"{prod['main_category']}_{prod['brand']}"
            if pk in collab_data["item_keys"]:
                ci = collab_data["item_enc"].transform([pk])[0]
                collab_scores[i] = raw_collab[ci]
 
    hybrid_scores = (0.5 * content_scores) + (0.5 * collab_scores)
 
    results = []
    for i in np.argsort(hybrid_scores)[::-1]:
        prod = products_df.iloc[i]
        if prod["main_category"] == category and prod["brand"] == brand:
            continue
        results.append({
            "product_id":    int(prod["product_id"]),
            "main_category": str(prod["main_category"]),
            "brand":         str(prod["brand"]),
            "price_range":   str(prod["price_range"]),
            "hybrid_score":  round(float(hybrid_scores[i]), 3)
        })
        if len(results) >= top_n:
            break
 
    return results

@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    if username == "admin" and password == "admin123":
        token = create_access_token(identity=username)
        return jsonify({"token": token, "message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/event", methods=["POST"])
@jwt_required()
def receive_event():
    '''
    Epsilon-style event endpoint.
    Accepts all 5 layers of data from partner companies.
 
    Full body example:
    {
        "user_id":      "user123",
        "event_type":   "purchase",        # view/search/cart/purchase/dismiss/click
        "category":     "electronics",
        "brand":        "samsung",
        "price_range":  "50k-70k",
        "product_name": "Samsung Galaxy S24",
        "search_query": "samsung phone",   # if event is search
        "session_id":   "sess_abc123",
        "device_id":    "device_xyz",
 
        # Layer 4: Demographics (optional — sent once, stored forever)
        "age_group":    "25-34",
        "gender":       "male",
        "city":         "Bengaluru",
        "state":        "Karnataka",
        "country":      "India",
        "device_type":  "mobile",
        "platform":     "android",
        "language":     "en"
    }
    '''
    if check_rate_limit(request.remote_addr):
        return jsonify({"error": "Too many requests"}), 429
 
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Valid JSON body is required"}), 400
    if not data.get("user_id"):
        return jsonify({"error": "user_id is required"}), 400
 
    # ── Sanitize inputs ───────────────────────────────────────
    user_id      = sanitize_string(str(data.get("user_id",      "")), 100)
    event_type   = sanitize_string(data.get("event_type",   "view"))
    category     = sanitize_string(data.get("category",     "unknown"))
    brand        = sanitize_string(data.get("brand",        "unknown"))
    price_range  = sanitize_string(data.get("price_range",  "unknown"))
    product_name = sanitize_string(data.get("product_name", ""))
    search_query = sanitize_string(data.get("search_query", ""))
    session_id   = sanitize_string(data.get("session_id",   ""))
    device_id    = sanitize_string(data.get("device_id",    ""))
 
    # Layer 4: Demographics
    age_group    = sanitize_string(data.get("age_group",   ""))
    gender       = sanitize_string(data.get("gender",      ""))
    city         = sanitize_string(data.get("city",        ""))
    state        = sanitize_string(data.get("state",       ""))
    country      = sanitize_string(data.get("country",     "India"))
    device_type  = sanitize_string(data.get("device_type", ""))
    platform     = sanitize_string(data.get("platform",    ""))
    language     = sanitize_string(data.get("language",    ""))
 
    ALLOWED_EVENTS = {"view", "search", "cart", "purchase", "dismiss", "click"}
    if event_type not in ALLOWED_EVENTS:
        return jsonify({"error": f"Invalid event_type. Use: {', '.join(ALLOWED_EVENTS)}"}), 400
 
    # Intelligence scoring weights
    SCORE_WEIGHTS = {
        "view":     {"interest": 0.5, "browse": 0.5,  "engagement": 0.0, "purchase": 0.0},
        "search":   {"interest": 0.3, "browse": 0.2,  "engagement": 0.3, "purchase": 0.0},
        "cart":     {"interest": 1.0, "browse": 0.0,  "engagement": 1.0, "purchase": 0.0},
        "click":    {"interest": 0.4, "browse": 0.0,  "engagement": 0.4, "purchase": 0.0},
        "purchase": {"interest": 2.0, "browse": 0.0,  "engagement": 0.5, "purchase": 2.0},
        "dismiss":  {"interest": -1.0,"browse": 0.0,  "engagement": 0.0, "purchase": 0.0},
    }
    weights = SCORE_WEIGHTS.get(event_type, SCORE_WEIGHTS["view"])
 
    price_estimate_map = {
        "0-500":250,"500-1k":750,"1k-5k":3000,
        "5k-10k":7500,"10k-30k":20000,"30k-70k":50000,"70k+":80000
    }
    estimated_price = price_estimate_map.get(price_range, 0)
 
    conn = cursor = None
    try:
        conn   = get_db()
        cursor = conn.cursor()
 
        # ── Layer 1: Identity Resolution ──────────────────────
        cursor.execute(
            "SELECT core_id FROM identities WHERE identifier_type='user_id' AND identifier_value=%s",
            (user_id,)
        )
        result = cursor.fetchone()
        if result:
            core_id = result[0]
        else:
            core_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO users (core_id) VALUES (%s)", (core_id,))
            cursor.execute(
                "INSERT INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,'user_id',%s)",
                (core_id, user_id)
            )
 
        # Link device_id too if provided
        if device_id:
            cursor.execute(
                "SELECT id FROM identities WHERE identifier_type='device_id' AND identifier_value=%s",
                (device_id,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT IGNORE INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,'device_id',%s)",
                    (core_id, device_id)
                )
 
        # ── Layer 2: Save interaction (Activity) ──────────────
        cursor.execute("""
            INSERT INTO interactions
                (core_id, event_type, main_category, brand, price_range,
                 product_name, search_query, session_id, device_type, source)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            core_id, event_type, category, brand, price_range,
            product_name or None, search_query or None,
            session_id or None, device_type or None, "api"
        ))
 
        # ── Layer 4: Demographics ──────────────────────────────
        if any([age_group, gender, city, state, device_type, platform, language]):
            cursor.execute(
                "SELECT demo_id FROM user_demographics WHERE core_id=%s", (core_id,)
            )
            demo_exists = cursor.fetchone()
            if demo_exists:
                updates, values = [], []
                if age_group:   updates.append("age_group=%s");   values.append(age_group)
                if gender:      updates.append("gender=%s");      values.append(gender)
                if city:        updates.append("city=%s");        values.append(city)
                if state:       updates.append("state=%s");       values.append(state)
                if country:     updates.append("country=%s");     values.append(country)
                if device_type: updates.append("device_type=%s"); values.append(device_type)
                if platform:    updates.append("platform=%s");    values.append(platform)
                if language:    updates.append("language=%s");    values.append(language)
                updates.append("updated_at=NOW()")
                values.append(core_id)
                cursor.execute(
                    f"UPDATE user_demographics SET {', '.join(updates)} WHERE core_id=%s",
                    values
                )
            else:
                cursor.execute("""
                    INSERT INTO user_demographics
                        (core_id, age_group, gender, city, state, country,
                         device_type, platform, language)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    core_id,
                    age_group or None, gender or None, city or None,
                    state or None, country or "India", device_type or None,
                    platform or None, language or None
                ))
 
        # ── Layer 3 + 5: Interest profile (Commerce + Intelligence) ──
        cursor.execute("""
            SELECT profile_id, interest_score, browse_score, purchase_score,
                   engagement_score, browse_count, cart_count, purchase_count,
                   dismiss_count, total_spent
            FROM interest_profiles
            WHERE core_id=%s AND main_category=%s AND brand=%s
        """, (core_id, category, brand))
        existing = cursor.fetchone()
 
        suppress_until = None
        if event_type == "purchase":
            lifetime = get_lifetime(cursor, category)
            suppress_until = datetime.now() + timedelta(days=lifetime)
        elif event_type == "dismiss":
            suppress_until = datetime.now() + timedelta(days=7)
 
        if existing:
            (pid, i_sc, b_sc, p_sc, e_sc,
             b_cnt, c_cnt, p_cnt, d_cnt, spent) = existing
 
            cursor.execute("""
                UPDATE interest_profiles
                SET interest_score   = %s, browse_score     = %s,
                    purchase_score   = %s, engagement_score = %s,
                    browse_count     = %s, cart_count       = %s,
                    purchase_count   = %s, dismiss_count    = %s,
                    total_spent      = %s, last_purchased   = %s,
                    suppress_until   = %s, updated_at       = NOW()
                WHERE profile_id = %s
            """, (
                max(0, i_sc + weights["interest"]),
                max(0, b_sc + weights["browse"]),
                max(0, p_sc + weights["purchase"]),
                max(0, e_sc + weights["engagement"]),
                b_cnt + (1 if event_type == "view"     else 0),
                c_cnt + (1 if event_type == "cart"     else 0),
                p_cnt + (1 if event_type == "purchase" else 0),
                d_cnt + (1 if event_type == "dismiss"  else 0),
                (spent or 0) + (estimated_price if event_type == "purchase" else 0),
                datetime.now() if event_type == "purchase" else None,
                suppress_until,
                pid
            ))
        else:
            cursor.execute("""
                INSERT INTO interest_profiles
                    (core_id, main_category, brand, price_range,
                     interest_score, browse_score, purchase_score, engagement_score,
                     browse_count, cart_count, purchase_count, dismiss_count,
                     total_spent, last_purchased, suppress_until)
                VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s)
            """, (
                core_id, category, brand, price_range,
                weights["interest"], weights["browse"],
                weights["purchase"], weights["engagement"],
                1 if event_type == "view"     else 0,
                1 if event_type == "cart"     else 0,
                1 if event_type == "purchase" else 0,
                1 if event_type == "dismiss"  else 0,
                estimated_price if event_type == "purchase" else 0,
                datetime.now() if event_type == "purchase" else None,
                suppress_until
            ))
 
        conn.commit()
        return jsonify({
            "success":   True,
            "core_id":   core_id,
            "message":   f"Event '{event_type}' recorded — all 5 layers updated",
            "layers_updated": {
                "identity":      True,
                "activity":      True,
                "commerce":      event_type in ["purchase", "cart"],
                "demographics":  bool(any([age_group, gender, city])),
                "intelligence":  True
            }
        }), 200
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


@app.route("/api/recommend/<user_id>", methods=["GET"])
@jwt_required()
def get_recommendations(user_id):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor2 = conn.cursor()
        core_id = resolve_identity(cursor2, user_id)
        conn.commit()
        cursor2.close()

        cursor.execute("""
            SELECT main_category, brand, price_range,
                   interest_score, suppress_until
            FROM interest_profiles
            WHERE core_id = %s
              AND (suppress_until IS NULL OR suppress_until < NOW())
            ORDER BY interest_score DESC
            LIMIT 1
        """, (core_id,))

        top_interest = cursor.fetchone()

        if not top_interest:
            cursor.execute("""
                SELECT main_category, suppress_until
                FROM interest_profiles
                WHERE core_id = %s
                ORDER BY interest_score DESC LIMIT 1
            """, (core_id,))
            suppressed_item = cursor.fetchone()

            cursor.close()
            conn.close()

            if suppressed_item:
                return jsonify({
                    "user_id":    user_id,
                    "core_id":    core_id,
                    "suppressed": True,
                    "message":    f"User recently purchased. No recommendations until {suppressed_item['suppress_until']}",
                    "recommendations": []
                }), 200
            else:
                return jsonify({
                    "user_id":    user_id,
                    "core_id":    core_id,
                    "message":    "No profile found for this user yet",
                    "recommendations": []
                }), 200

        recommendations = find_similar_products(
            category    = top_interest["main_category"],
            brand       = top_interest["brand"],
            price_range = top_interest["price_range"]
        )

        cursor.close()
        conn.close()

        return jsonify({
            "user_id":      user_id,
            "core_id":      core_id,
            "suppressed":   False,
            "top_interest": {
                "category":    top_interest["main_category"],
                "brand":       top_interest["brand"],
                "price_range": top_interest["price_range"],
                "score":       top_interest["interest_score"]
            },
            "recommendations": recommendations,
            "total":           len(recommendations)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile/<user_id>", methods=["GET"])
@jwt_required()
def get_profile(user_id):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Resolve identity
        cursor2 = conn.cursor()
        core_id = resolve_identity(cursor2, user_id)
        conn.commit()
        cursor2.close()

        cursor.execute("""
            SELECT main_category, brand, price_range,
                   interest_score, browse_count, purchase_count,
                   last_purchased, suppress_until, updated_at
            FROM interest_profiles
            WHERE core_id = %s
            ORDER BY interest_score DESC
        """, (core_id,))

        profiles = cursor.fetchall()

        # Get all identities linked to this user
        cursor.execute("""
            SELECT identifier_type, identifier_value, created_at
            FROM identities
            WHERE core_id = %s
        """, (core_id,))
        identities = cursor.fetchall()

        # Get total interactions count
        cursor.execute(
            "SELECT COUNT(*) as total FROM interactions WHERE core_id=%s",
            (core_id,)
        )
        interaction_count = cursor.fetchone()["total"]

        cursor.close()
        conn.close()

        # Convert datetime objects to strings for JSON
        for p in profiles:
            for key in ["last_purchased", "suppress_until", "updated_at"]:
                if p[key]:
                    p[key] = str(p[key])

        for i in identities:
            if i["created_at"]:
                i["created_at"] = str(i["created_at"])

        return jsonify({
            "user_id":          user_id,
            "core_id":          core_id,
            "total_interactions": interaction_count,
            "identities":       identities,
            "interest_profiles": profiles,
            "profile_count":    len(profiles)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route("/api/profile360/<user_id>", methods=["GET"])
@jwt_required()
def get_profile_360(user_id):
    '''
    Returns full Epsilon-style 360 profile for a user.
    Shows all 5 layers: Identity, Activity, Commerce,
    Demographics, and Intelligence scores.
    '''
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
 
        # Resolve identity
        cursor2 = conn.cursor()
        core_id = resolve_identity(cursor2, user_id)
        conn.commit()
        cursor2.close()
 
        cursor.execute(
            "SELECT identifier_type, identifier_value, created_at FROM identities WHERE core_id=%s",
            (core_id,)
        )
        identities = cursor.fetchall()
 
        cursor.execute("""
            SELECT event_type, main_category, brand, price_range,
                   product_name, search_query, device_type, event_time
            FROM interactions
            WHERE core_id=%s
            ORDER BY event_time DESC LIMIT 20
        """, (core_id,))
        recent_activity = cursor.fetchall()
 
        cursor.execute("""
            SELECT main_category, brand, price_range,
                   purchase_count, total_spent, last_purchased
            FROM interest_profiles
            WHERE core_id=%s AND purchase_count > 0
            ORDER BY total_spent DESC
        """, (core_id,))
        purchase_history = cursor.fetchall()
 
        cursor.execute(
            "SELECT * FROM user_demographics WHERE core_id=%s", (core_id,)
        )
        demographics = cursor.fetchone()
 
        cursor.execute("""
            SELECT main_category, brand, price_range,
                   interest_score, browse_score, purchase_score,
                   engagement_score, browse_count, cart_count,
                   dismiss_count, suppress_until
            FROM interest_profiles
            WHERE core_id=%s
            ORDER BY interest_score DESC
        """, (core_id,))
        interest_scores = cursor.fetchall()
 
        # Total interactions
        cursor.execute(
            "SELECT COUNT(*) as total FROM interactions WHERE core_id=%s", (core_id,)
        )
        total_interactions = cursor.fetchone()["total"]
 
        cursor.close()
        conn.close()
 
        # Convert datetimes to strings
        for item in recent_activity + purchase_history + (interest_scores or []):
            for k, v in item.items():
                if hasattr(v, 'isoformat'):
                    item[k] = str(v)
        if demographics:
            for k, v in demographics.items():
                if hasattr(v, 'isoformat'):
                    demographics[k] = str(v)
        for i in identities:
            if i.get("created_at"):
                i["created_at"] = str(i["created_at"])
 
        return jsonify({
            "user_id":   user_id,
            "core_id":   core_id,
            "total_interactions": total_interactions,
            "layer_1_identity": {
                "core_id":    core_id,
                "identifiers": identities
            },
            "layer_2_activity": {
                "recent_events": recent_activity,
                "total_events":  total_interactions
            },
            "layer_3_commerce": {
                "purchase_history": purchase_history,
                "total_categories_purchased": len(purchase_history)
            },
            "layer_4_demographics": demographics or {},
            "layer_5_intelligence": {
                "interest_profiles": interest_scores,
                "top_interest": interest_scores[0] if interest_scores else None
            }
        }), 200
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Returns summary counts for dashboard cards."""

    conn = None
    cursor = None

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM interactions")
        total_interactions = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM notifications")
        total_notifications = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM interest_profiles
            WHERE suppress_until IS NULL OR suppress_until < NOW()
        """)
        active_profiles = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT main_category, COUNT(*) as cnt
            FROM interest_profiles
            GROUP BY main_category
            ORDER BY cnt DESC LIMIT 1
        """)
        top_cat = cursor.fetchone()

        cursor.execute("""
            SELECT brand, COUNT(*) as cnt
            FROM interest_profiles
            WHERE brand != 'unknown'
            GROUP BY brand
            ORDER BY cnt DESC LIMIT 1
        """)
        top_brand = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "total_users":        total_users,
            "total_interactions": total_interactions,
            "total_notifications": total_notifications,
            "active_profiles":    active_profiles,
            "top_category":       top_cat["main_category"] if top_cat else "N/A",
            "top_brand":          top_brand["brand"] if top_brand else "N/A"
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/api/dashboard/profiles", methods=["GET"])
def dashboard_profiles():
    """Returns paginated user profiles for dashboard table."""
    try:
        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1
        
        per_page = int(request.args.get("per_page", 20))
        offset   = (page - 1) * per_page

        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                ip.core_id,
                ip.main_category,
                ip.brand,
                ip.price_range,
                ip.interest_score,
                ip.browse_count,
                ip.purchase_count,
                ip.suppress_until,
                ip.updated_at,
                u.email
            FROM interest_profiles ip
            JOIN users u ON ip.core_id = u.core_id
            ORDER BY ip.interest_score DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

        profiles = cursor.fetchall()

        # Total count for pagination
        cursor.execute("SELECT COUNT(*) as total FROM interest_profiles")
        total = cursor.fetchone()["total"]

        cursor.close()
        conn.close()

        # Convert datetime to string
        for p in profiles:
            p["core_id"] = (p["core_id"][:8] + "...") if p["core_id"] else None
            p["suppress_until"] = str(p["suppress_until"]) if p["suppress_until"] else None
            p["updated_at"]   = str(p["updated_at"]) if p["updated_at"] else None
            p["suppressed"]   = p["suppress_until"] is not None

        return jsonify({
            "profiles": profiles,
            "total":    total,
            "page":     page,
            "per_page": per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/notifications", methods=["GET"])
def dashboard_notifications():
    """Returns recent notifications for dashboard table."""
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                n.notification_id,
                n.core_id,
                n.channel,
                n.message,
                n.product_ids,
                n.status,
                n.sent_at,
                u.email
            FROM notifications n
            JOIN users u ON n.core_id = u.core_id
            ORDER BY n.sent_at DESC
            LIMIT 50
        """)

        notifications = cursor.fetchall()
        cursor.close()
        conn.close()

        for n in notifications:
            n["core_id"] = (n["core_id"][:8] + "...") if n["core_id"] else None
            n["sent_at"]  = str(n["sent_at"]) if n["sent_at"] else None

        return jsonify({"notifications": notifications}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/categories", methods=["GET"])
def dashboard_categories():
    """Returns category breakdown for chart."""
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT main_category, COUNT(*) as count
            FROM interest_profiles
            GROUP BY main_category
            ORDER BY count DESC
            LIMIT 8
        """)
        categories = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"categories": categories}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
@jwt_required()
def receive_feedback():
    data     = request.get_json()
    user_id  = data.get("user_id")
    category = data.get("category", "unknown")
    brand    = data.get("brand",    "unknown")
    action   = data.get("action",   "ignored")

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    score_delta_map = {
        "clicked":   +1.0,
        "ignored":   -0.5,
        "dismissed": -1.0
    }
    score_delta = score_delta_map.get(action, -0.5)

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Resolve identity
        cursor2 = conn.cursor()
        core_id = resolve_identity(cursor2, user_id)
        conn.commit()
        cursor2.close()

        # Get current profile
        cursor.execute('''
            SELECT profile_id, interest_score, browse_count
            FROM interest_profiles
            WHERE core_id=%s AND main_category=%s AND brand=%s
        ''', (core_id, category, brand))

        profile = cursor.fetchone()

        if profile:
            new_score = max(0, profile["interest_score"] + score_delta)

            suppress_until = None
            if action == "dismissed":
                suppress_until = datetime.now() + timedelta(days=7)
                print(f"User dismissed {category}/{brand} — suppressing 7 days")

            cursor.execute('''
                UPDATE interest_profiles
                SET interest_score = %s,
                    suppress_until = %s,
                    updated_at     = NOW()
                WHERE profile_id = %s
            ''', (new_score, suppress_until, profile["profile_id"]))

        else:
            new_score = max(0, 1.0 + score_delta)
            cursor.execute('''
                INSERT INTO interest_profiles
                    (core_id, main_category, brand, interest_score)
                VALUES (%s, %s, %s, %s)
            ''', (core_id, category, brand, new_score))

        # Update notification status if exists
        cursor.execute('''
            UPDATE notifications
            SET status = %s
            WHERE core_id = %s
              AND message LIKE %s
            ORDER BY sent_at DESC
            LIMIT 1
        ''', (action, core_id, f"%{category}%"))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success":    True,
            "user_id":    user_id,
            "action":     action,
            "new_score":  round(new_score, 2),
            "message":    f"Feedback recorded — score updated to {round(new_score,2)}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


SWAGGER_URL  = '/docs'
API_URL      = '/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "CPRP API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


@app.route('/swagger.json')
def swagger_spec():
    return jsonify({
        "swagger": "2.0",
        "info": {
            "title":       "CPRP — Contextual Product Recommender API",
            "description": "Mini Epsilon-style platform for user profiling and product recommendations",
            "version":     "1.0.0",
            "contact": {
                "name":  "Vignesh",
                "email": "1MS24MC105@msrit.edu"
            }
        },
        "host":     "localhost:5000",
        "basePath": "/",
        "schemes":  ["http"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in":   "header",
                "description": "JWT token. Format: Bearer <token>"
            }
        },
        "paths": {
            "/api/login": {
                "post": {
                    "summary":     "Get JWT token",
                    "description": "Login with admin credentials to get access token",
                    "parameters": [{
                        "in": "body", "name": "body",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string", "example": "admin"},
                                "password": {"type": "string", "example": "admin123"}
                            }
                        }
                    }],
                    "responses": {
                        "200": {"description": "Returns JWT token"},
                        "401": {"description": "Invalid credentials"}
                    }
                }
            },
            "/api/event": {
                "post": {
                    "summary":     "Send user event",
                    "description": "XYZ company sends a browse/purchase event for a user",
                    "security":    [{"Bearer": []}],
                    "parameters": [{
                        "in": "body", "name": "body",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "user_id":    {"type": "string",  "example": "user123"},
                                "event_type": {"type": "string",  "example": "purchase"},
                                "category":   {"type": "string",  "example": "electronics"},
                                "brand":      {"type": "string",  "example": "samsung"},
                                "price_range":{"type": "string",  "example": "50k-70k"},
                                "email":      {"type": "string",  "example": "user@gmail.com"}
                            }
                        }
                    }],
                    "responses": {
                        "200": {"description": "Event recorded, profile updated"},
                        "400": {"description": "Missing user_id"}
                    }
                }
            },
            "/api/recommend/{user_id}": {
                "get": {
                    "summary":     "Get recommendations",
                    "description": "Returns personalized product recommendations for a user",
                    "security":    [{"Bearer": []}],
                    "parameters": [{
                        "in": "path", "name": "user_id",
                        "type": "string", "required": True,
                        "description": "The user ID to get recommendations for"
                    }],
                    "responses": {
                        "200": {"description": "List of recommended products"}
                    }
                }
            },
            "/api/profile/{user_id}": {
                "get": {
                    "summary":     "Get user profile",
                    "description": "Returns the 360-degree interest profile for a user",
                    "security":    [{"Bearer": []}],
                    "parameters": [{
                        "in": "path", "name": "user_id",
                        "type": "string", "required": True
                    }],
                    "responses": {
                        "200": {"description": "Full user profile with interest scores"}
                    }
                }
            },
            "/api/feedback": {
                "post": {
                    "summary":     "Send notification feedback",
                    "description": "User clicked/ignored/dismissed a recommendation",
                    "security":    [{"Bearer": []}],
                    "parameters": [{
                        "in": "body", "name": "body",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "user_id":  {"type": "string", "example": "user123"},
                                "category": {"type": "string", "example": "electronics"},
                                "brand":    {"type": "string", "example": "samsung"},
                                "action":   {"type": "string", "example": "clicked",
                                             "enum": ["clicked", "ignored", "dismissed"]}
                            }
                        }
                    }],
                    "responses": {
                        "200": {"description": "Feedback recorded, score updated"}
                    }
                }
            },
            "/api/health": {
                "get": {
                    "summary":  "Health check",
                    "responses": {"200": {"description": "API is running"}}
                }
            }
        }
    })

import pathlib
_PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)

@app.route("/dashboard")
def dashboard():
    """Serves the dashboard HTML file."""
    return send_from_directory(_PROJECT_ROOT, "dashboard.html")

@app.route("/dashboard.css")
def dashboard_css():
    """Serves the dashboard CSS file."""
    return send_from_directory(_PROJECT_ROOT, "dashboard.css")

@app.route("/dashboard.js")
def dashboard_js():
    """Serves the dashboard JS file."""
    return send_from_directory(_PROJECT_ROOT, "dashboard.js")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":       "ok",
        "model_loaded": model_data is not None,
        "timestamp":    str(datetime.now())
    }), 200


if __name__ == "__main__":
    print("=" * 50)
    print("  CPRP - Flask API Server")
    print("  Running on http://localhost:5000")
    print("=" * 50)
    print("\nEndpoints:")
    print("  POST /api/login")
    print("  POST /api/event")
    print("  GET  /api/recommend/<user_id>")
    print("  GET  /api/profile/<user_id>")
    print("  GET  /api/health")
    print("\nPress Ctrl+C to stop\n")

    app.run(
        host  = "0.0.0.0",
        port  = 5000,
        debug = True
    )