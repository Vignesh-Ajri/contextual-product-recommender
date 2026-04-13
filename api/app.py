# ============================================================
# STEP 6 - Flask API
# File: api/app.py
#
# What this does:
# - Starts a web server on http://localhost:5000
# - Exposes 3 API endpoints:
#
#   POST /api/event
#     → Any company sends a user event (browse/purchase)
#     → Creates/updates user profile in MySQL
#     → This replaces the JS snippet — any company can call this
#
#   GET /api/recommend/<user_id>
#     → Returns personalized product recommendations for a user
#     → Loads ML model → finds similar products → checks suppression
#
#   GET /api/profile/<user_id>
#     → Returns the full interest profile for a user
#     → Shows their 4 parameters + interest scores
#
# Command: python api/app.py
# Test with: Postman or browser
# ============================================================

import pandas as pd
import joblib                              # load saved ML model
import uuid                                # generate unique IDs
import mysql.connector                     # connect to MySQL
from datetime import datetime, timedelta   # date calculations
from flask import Flask, request, jsonify, send_from_directory  # web framework
from flask_jwt_extended import (           # JWT authentication
    JWTManager, jwt_required, create_access_token, get_jwt_identity
)
import os
from dotenv import load_dotenv
load_dotenv()

# ── 1. App setup ──────────────────────────────────────────────
app = Flask(__name__)

# Secret key for JWT tokens — change this to something random in production
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)


# ── 2. Database config ────────────────────────────────────────
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


# ── 3. Load ML model ──────────────────────────────────────────
# Load the trained model once when the server starts
# We don't reload it on every request (that would be slow)
print("Loading ML model...")
try:
    tfidf             = joblib.load("ml/tfidf.pkl")
    similarity_matrix = joblib.load("ml/cosine_sim.pkl")
    products_df       = pd.read_csv("ml/products.csv")
    model_data        = True   # just marks model as loaded

    print(f"✅ Model loaded — {len(products_df)} products in catalog")
except FileNotFoundError:
    print("⚠️  Model not found. Run ml/train_model.py first!")
    print("    API will start but /recommend endpoint won't work until model is trained")
    model_data = None


# ── 4. Helper: resolve identity ───────────────────────────────
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

    # New user — create fresh core_id
    new_core_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO users (core_id) VALUES (%s)", (new_core_id,))
    cursor.execute(
        "INSERT INTO identities (core_id, identifier_type, identifier_value) VALUES (%s,%s,%s)",
        (new_core_id, id_type, str(identifier))
    )
    return new_core_id


# ── 5. Helper: get product lifetime ──────────────────────────
def get_lifetime(cursor, category):
    """Get suppression days for a product category."""
    cursor.execute(
        "SELECT lifetime_days FROM product_lifetime WHERE main_category=%s",
        (category,)
    )
    result = cursor.fetchone()
    return result[0] if result else 90


# ── 6. Helper: get recommendations from model ─────────────────
def find_similar_products(category, brand, price_range, top_n=5):
    """
    Use the trained ML model to find similar products.
    Returns a list of product dicts.
    """
    if model_data is False:
        return []

    # Find matching product in catalog
    match = products_df[
        (products_df["main_category"] == category) &
        (products_df["brand"]         == brand)
    ]

    # Fall back to category only if brand not found
    if len(match) == 0:
        match = products_df[products_df["main_category"] == category]

    if len(match) == 0:
        return []

    idx = match.index[0]

    # Get similarity scores, sort highest first
    scores = list(enumerate(similarity_matrix[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = [s for s in scores if s[0] != idx]   # remove self

    top_indices = [s[0] for s in scores[:top_n]]

    return products_df.iloc[top_indices][
        ["product_id", "main_category", "brand", "price_range"]
    ].to_dict("records")


# ══════════════════════════════════════════════════════════════
# ENDPOINT 1: Login (get JWT token)
# POST /api/login
# Body: { "username": "admin", "password": "admin123" }
# Returns: { "token": "eyJ..." }
#
# Use this token in all other requests as:
# Header: Authorization: Bearer <token>
# ══════════════════════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    # Simple hardcoded admin check
    # In real project: check against database
    if username == "admin" and password == "admin123":
        token = create_access_token(identity=username)
        return jsonify({"token": token, "message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401


# ══════════════════════════════════════════════════════════════
# ENDPOINT 2: Receive a user event
# POST /api/event
# Headers: Authorization: Bearer <token>
#
# Body example:
# {
#   "user_id":      "user123",
#   "event_type":   "purchase",
#   "category":     "electronics",
#   "brand":        "samsung",
#   "price_range":  "50k-70k",
#   "product_name": "Samsung Galaxy S24"
# }
#
# This is what XYZ company calls to send their user data to you.
# Replaces the JS tracker — any company can POST here.
# ══════════════════════════════════════════════════════════════
@app.route("/api/event", methods=["POST"])
@jwt_required()
def receive_event():
    data = request.get_json()

    # Validate required fields
    if not data or "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    user_id    = data.get("user_id")
    event_type = data.get("event_type",  "view")
    category   = data.get("category",    "unknown")
    brand      = data.get("brand",       "unknown")
    price_range = data.get("price_range", "unknown")

    try:
        conn   = get_db()
        cursor = conn.cursor()

        # Step 1: Resolve identity → get core_id
        core_id = resolve_identity(cursor, user_id)

        # Step 2: Save interaction
        cursor.execute("""
            INSERT INTO interactions
                (core_id, event_type, main_category, brand, price_range, source)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (core_id, event_type, category, brand, price_range, "api"))

        # Step 3: Update interest profile
        score_map   = {"view": 0.5, "cart": 1.0, "purchase": 2.0}
        score_delta = score_map.get(event_type, 0.5)

        # Check if profile row exists
        cursor.execute("""
            SELECT profile_id, interest_score, browse_count, purchase_count
            FROM interest_profiles
            WHERE core_id=%s AND main_category=%s AND brand=%s
        """, (core_id, category, brand))

        existing = cursor.fetchone()

        if existing:
            new_score    = existing[1] + score_delta
            new_browse   = existing[2] + (1 if event_type == "view" else 0)
            new_purchase = existing[3] + (1 if event_type == "purchase" else 0)

            suppress_until = None
            if event_type == "purchase":
                lifetime = get_lifetime(cursor, category)
                suppress_until = datetime.now() + timedelta(days=lifetime)

            cursor.execute("""
                UPDATE interest_profiles
                SET interest_score=%s, browse_count=%s, purchase_count=%s,
                    last_purchased=%s, suppress_until=%s, updated_at=NOW()
                WHERE profile_id=%s
            """, (
                new_score, new_browse, new_purchase,
                datetime.now() if event_type == "purchase" else None,
                suppress_until,
                existing[0]
            ))
        else:
            suppress_until = None
            if event_type == "purchase":
                lifetime = get_lifetime(cursor, category)
                suppress_until = datetime.now() + timedelta(days=lifetime)

            cursor.execute("""
                INSERT INTO interest_profiles
                    (core_id, main_category, brand, price_range,
                     interest_score, browse_count, purchase_count,
                     last_purchased, suppress_until)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                core_id, category, brand, price_range,
                score_delta,
                1 if event_type == "view" else 0,
                1 if event_type == "purchase" else 0,
                datetime.now() if event_type == "purchase" else None,
                suppress_until
            ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success":  True,
            "core_id":  core_id,
            "message":  f"Event '{event_type}' recorded for user {user_id}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════
# ENDPOINT 3: Get recommendations for a user
# GET /api/recommend/<user_id>
# Headers: Authorization: Bearer <token>
#
# Response example:
# {
#   "user_id": "user123",
#   "core_id": "a1b2-c3d4-...",
#   "top_interest": { "category": "electronics", "brand": "samsung" },
#   "recommendations": [
#     { "main_category": "electronics", "brand": "apple", "price_range": "50k-70k" },
#     ...
#   ],
#   "suppressed": false
# }
# ══════════════════════════════════════════════════════════════
@app.route("/api/recommend/<user_id>", methods=["GET"])
@jwt_required()
def get_recommendations(user_id):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)   # dictionary=True returns rows as dicts

        # Step 1: Resolve identity
        cursor2 = conn.cursor()
        core_id = resolve_identity(cursor2, user_id)
        conn.commit()
        cursor2.close()

        # Step 2: Get user's top interest (highest score, not suppressed)
        cursor.execute("""
            SELECT main_category, brand, price_range,
                   interest_score, suppress_until
            FROM interest_profiles
            WHERE core_id = %s
              AND (suppress_until IS NULL OR suppress_until < NOW())
            ORDER BY interest_score DESC
            LIMIT 1
        """, (core_id,))
        # suppress_until < NOW() = suppression period is over

        top_interest = cursor.fetchone()

        if not top_interest:
            # User has no profile yet OR everything is suppressed
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

        # Step 3: Find similar products using ML model
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


# ══════════════════════════════════════════════════════════════
# ENDPOINT 4: Get full user profile
# GET /api/profile/<user_id>
# Headers: Authorization: Bearer <token>
#
# Returns the complete 360° profile — all categories, scores, suppression
# This is your "Customer+" unified profile view
# ══════════════════════════════════════════════════════════════
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

        # Get all interest profiles for this user
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
    
# ============================================================
# DASHBOARD ROUTES — add these to the bottom of api/app.py
# (paste above the if __name__ == "__main__": line)
#
# These 4 routes power the HTML dashboard:
#   GET /dashboard              → serves the HTML page
#   GET /api/stats              → total counts for top cards
#   GET /api/dashboard/profiles → all user profiles
#   GET /api/dashboard/notifications → all notifications sent
# ============================================================

# ── Dashboard stats (top 4 cards) ────────────────────────────
@jwt_required()
@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Returns summary counts for dashboard cards."""

    conn = None
    cursor = None

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Total unique users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()["count"]

        # Total interactions
        cursor.execute("SELECT COUNT(*) as count FROM interactions")
        total_interactions = cursor.fetchone()["count"]

        # Total notifications sent
        cursor.execute("SELECT COUNT(*) as count FROM notifications")
        total_notifications = cursor.fetchone()["count"]

        # Active profiles (not suppressed)
        cursor.execute("""
            SELECT COUNT(*) as count FROM interest_profiles
            WHERE suppress_until IS NULL OR suppress_until < NOW()
        """)
        active_profiles = cursor.fetchone()["count"]

        # Top category
        cursor.execute("""
            SELECT main_category, COUNT(*) as cnt
            FROM interest_profiles
            GROUP BY main_category
            ORDER BY cnt DESC LIMIT 1
        """)
        top_cat = cursor.fetchone()

        # Top brand
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

# ── User profiles list ────────────────────────────────────────
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


# ── Notifications list ────────────────────────────────────────
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


# ── Serve dashboard HTML ──────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    """Serves the dashboard HTML file."""
    return send_from_directory(".", "dashboard.html")


# ── Category breakdown ────────────────────────────────────────
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


# ── 7. Health check ───────────────────────────────────────────
# Simple endpoint to check if server is running
# GET /api/health → { "status": "ok" }
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":       "ok",
        "model_loaded": model_data is not None,
        "timestamp":    str(datetime.now())
    }), 200


# ── 8. Start server ───────────────────────────────────────────
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
        host  = "0.0.0.0",   # accessible from any device on same network
        port  = 5000,
        debug = True          # shows errors in browser — turn off in production
    )