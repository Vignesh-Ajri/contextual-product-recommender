# ============================================================
# CPRP — FastAPI Application
# File: api/app.py
#
# Endpoints:
#   GET  /                          — welcome + model info
#   GET  /health                    — model, MySQL, Redis, Kafka status
#   POST /event                     — ingest user event → Kafka → MySQL
#   GET  /recommend/{user_id}       — personalised recs from MySQL profiles
#   GET  /recommend/cold/{category} — cold-start (no history needed)
#   GET  /profile/{user_id}         — view full MySQL interest profile
#   GET  /catalog/categories        — list all categories
#   GET  /catalog/brands            — list brands (optional filter)
#   GET  /metrics                   — live P@K / F1@K evaluation
#
# Run:
#   uvicorn api.app:app --reload --port 8000
# ============================================================

import os
import time
import json
import math
import numpy as np
import mysql.connector
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from api.recommend_engine import RecommendEngine
from api import cache

load_dotenv()

# ── DB config ─────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 3307)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC     = os.getenv("KAFKA_TOPIC_EVENTS",      "user_events")

# ── Globals ────────────────────────────────────────────────────
engine:   RecommendEngine = None
producer: KafkaProducer   = None
kafka_ok: bool            = False


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def init_kafka_producer():
    global producer, kafka_ok
    try:
        producer = KafkaProducer(
            bootstrap_servers = KAFKA_BOOTSTRAP,
            value_serializer  = lambda v: json.dumps(v).encode("utf-8"),
            key_serializer    = lambda k: k.encode("utf-8") if k else None,
            acks              = 1,
            retries           = 3,
            request_timeout_ms= 5000,
            linger_ms         = 5,
        )
        kafka_ok = True
        print(f"[Kafka] Producer connected → {KAFKA_BOOTSTRAP}")
    except NoBrokersAvailable:
        kafka_ok = False
        print("[Kafka] Broker unavailable — events saved to MySQL only")
    except Exception as e:
        kafka_ok = False
        print(f"[Kafka] Producer error: {e}")


# ── Startup / shutdown ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    print("\n[CPRP] Starting up...")
    engine = RecommendEngine()
    init_kafka_producer()
    print("[CPRP] API ready.\n")
    yield
    print("[CPRP] Shutting down...")
    if producer and kafka_ok:
        try:
            producer.flush(timeout=5)
            producer.close(timeout=5)
        except Exception:
            pass
    print("[CPRP] Done.")


# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title       = "CPRP — Contextual Product Recommender Platform",
    description = (
        "Epsilon-style recommendation system. "
        "Hybrid BM25 + ALS + Sentence-Embedding model. "
        "Kafka event streaming → MySQL profiles → ranked recommendations. "
        "Ramaiah Institute of Technology MCA Project."
    ),
    version  = "3.0.0",
    lifespan = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

DASHBOARD_DIR = pathlib.Path(__file__).resolve().parent.parent / "dashboard"
if DASHBOARD_DIR.exists():
    app.mount("/dashboard/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="dashboard_static")


# ── Admin Dashboard Endpoints ──────────────────────────────────

@app.get("/dashboard", tags=["Dashboard"], include_in_schema=False)
def serve_dashboard():
    """Serve the admin dashboard HTML page."""
    index = DASHBOARD_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(404, "Dashboard not found")


@app.get("/api/admin/stats", tags=["Dashboard"])
def admin_stats():
    """Overview statistics for the admin dashboard."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM users WHERE email IS NOT NULL AND email != ''")
        users_with_email = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM interactions")
        total_interactions = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(DISTINCT core_id) as total FROM interest_profiles")
        profiled_users = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM interest_profiles WHERE suppress_until IS NOT NULL AND suppress_until > NOW()")
        suppressed_profiles = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM interest_profiles WHERE interest_score >= 3.0 AND suppress_until IS NULL")
        high_interest = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(DISTINCT main_category) as total FROM product_lifetime")
        categories = cursor.fetchone()["total"]

        return {
            "total_users": total_users,
            "users_with_email": users_with_email,
            "total_interactions": total_interactions,
            "profiled_users": profiled_users,
            "suppressed_profiles": suppressed_profiles,
            "high_interest_alerts": high_interest,
            "product_categories": categories,
        }
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/profiles", tags=["Dashboard"])
def admin_profiles(limit: int = Query(50, ge=1, le=200)):
    """List user interest profiles with scores."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ip.core_id, u.email, ip.main_category, ip.brand,
                   ip.interest_score, ip.browse_count, ip.cart_count,
                   ip.purchase_count, ip.dismiss_count, ip.total_spent,
                   ip.last_purchased, ip.suppress_until, ip.last_notified_at,
                   ip.updated_at
            FROM interest_profiles ip
            LEFT JOIN users u ON ip.core_id = u.core_id
            ORDER BY ip.interest_score DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        for row in rows:
            for key in row:
                if hasattr(row[key], 'isoformat'):
                    row[key] = row[key].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/lifetimes", tags=["Dashboard"])
def admin_lifetimes():
    """List all product lifetime configurations."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM product_lifetime ORDER BY lifetime_days ASC")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@app.put("/api/admin/lifetimes/{category}", tags=["Dashboard"])
def update_lifetime(category: str, lifetime_days: int = Query(..., ge=1, le=365)):
    """Update product lifetime for a category."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE product_lifetime SET lifetime_days = %s WHERE main_category = %s",
            (lifetime_days, category)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, f"Category '{category}' not found")
        return {"message": f"Updated {category} to {lifetime_days} days"}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/activity", tags=["Dashboard"])
def admin_activity(limit: int = Query(20, ge=1, le=100)):
    """Recent interaction activity feed."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT i.core_id, u.email, i.event_type, i.main_category,
                   i.brand, i.product_name, i.event_time
            FROM interactions i
            LEFT JOIN users u ON i.core_id = u.core_id
            ORDER BY i.event_time DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        for row in rows:
            for key in row:
                if hasattr(row[key], 'isoformat'):
                    row[key] = row[key].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


# ── Schemas ────────────────────────────────────────────────────
class EventRequest(BaseModel):
    user_id:     str = Field(..., max_length=100, json_schema_extra={"example": "vignesh_001"})
    event_type:  str = Field(..., max_length=50, json_schema_extra={"example": "purchase"},
                             description="view|search|cart|wishlist|purchase|ignore|dismiss")
    category:    str = Field(..., max_length=100, json_schema_extra={"example": "mouthwash"})
    brand:       str = Field(..., max_length=100, json_schema_extra={"example": "listerine"})
    price_range: str = Field("unknown", max_length=50, json_schema_extra={"example": "200-500"})
    product_name:str = Field("", max_length=255, json_schema_extra={"example": "Listerine Cool Mint"})
    # Optional Epsilon Layer 4 — demographics
    age_group:   str = Field("", max_length=20, json_schema_extra={"example": "25-34"})
    gender:      str = Field("", max_length=20, json_schema_extra={"example": "male"})
    city:        str = Field("", max_length=100, json_schema_extra={"example": "Bengaluru"})
    state:       str = Field("", max_length=100, json_schema_extra={"example": "Karnataka"})
    country:     str = Field("India", max_length=50, json_schema_extra={"example": "India"})
    device_type: str = Field("", max_length=50, json_schema_extra={"example": "mobile"})
    platform:    str = Field("", max_length=50, json_schema_extra={"example": "android"})
    email:       str = Field("", max_length=255, json_schema_extra={"example": "user@example.com"})


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/", tags=["General"])
def root():
    return {
        "project": "CPRP — Contextual Product Recommender Platform",
        "version": "3.0.0",
        "model":   engine.model_label if engine else "loading...",
        "docs":    "/docs",
        "health":  "/health",
    }


@app.get("/health", tags=["General"])
def health():
    """
    Check all services: ML model, MySQL, Redis, Kafka.
    Use after startup to confirm everything is connected.
    """
    # MySQL check
    mysql_status = {"connected": False}
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        cursor.close(); conn.close()
        mysql_status = {"connected": True, "total_users": count}
    except Exception as e:
        mysql_status = {"connected": False, "error": str(e)}

    return {
        "status":    "ok",
        "model":     engine.model_label if engine else "not loaded",
        "products":  len(engine.products) if engine else 0,
        "mysql":     mysql_status,
        "redis":     cache.cache_stats(),
        "kafka": {
            "available":  kafka_ok,
            "bootstrap":  KAFKA_BOOTSTRAP,
            "topic":      KAFKA_TOPIC,
        },
        "timestamp": time.time(),
    }


@app.post("/event", tags=["Events"])
def ingest_event(req: EventRequest):
    """
    Ingest a user event.

    Flow:
      1. Publish to Kafka topic (user_events) — non-blocking
      2. kafka/consumer.py picks it up and writes to MySQL
         (identity resolution, interaction log, interest profile update)

    Kafka unavailable? The event is still logged directly to MySQL
    via the fallback path so no data is ever lost.

    Event weights:
      purchase +2.0 | cart +1.0 | wishlist +0.8 | view +0.5
      search +0.3 | ignore -0.3 | dismiss -1.0
    """
    t0 = time.time()

    message = {
        "user_id":      req.user_id,
        "event_type":   req.event_type,
        "category":     req.category,
        "brand":        req.brand,
        "price_range":  req.price_range,
        "product_name": req.product_name,
        # Layer 4 demographics
        "age_group":    req.age_group,
        "gender":       req.gender,
        "city":         req.city,
        "state":        req.state,
        "country":      req.country,
        "device_type":  req.device_type,
        "platform":     req.platform,
        "source":       "api",
    }

    published = False
    if kafka_ok and producer:
        try:
            producer.send(KAFKA_TOPIC, key=req.user_id, value=message)
            published = True
        except Exception as e:
            print(f"[Kafka] Publish failed: {e}")

    # Direct MySQL fallback when Kafka is unavailable
    # Mirrors what consumer.py does for event_type + interest profile
    if not published:
        _direct_mysql_event(
            req.user_id, req.event_type, req.category,
            req.brand, req.price_range, req.product_name,
        )

    # Invalidate stale cached recs for this user
    cache.invalidate_user(req.user_id)

    return {
        "status":    "recorded",
        "user_id":   req.user_id,
        "event":     req.event_type,
        "category":  req.category,
        "brand":     req.brand,
        "delivery":  "kafka" if published else "mysql_direct",
        "latency_ms": round((time.time() - t0) * 1000, 2),
    }


# 1x1 Transparent GIF Binary
TRANSPARENT_GIF = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'

from fastapi import Request, Response, Cookie

@app.get("/api/v1/pixel.gif", tags=["Analytics"])
def tracking_pixel(
    request: Request,
    event: str = "view",
    category: str = "unknown",
    brand: str = "unknown",
    price_range: str = "unknown",
    product_name: str = "",
    visitor_id: Optional[str] = Cookie(None)
):
    """
    Epsilon-Style Tracking Pixel.
    Exposes a 1x1 transparent image to collect client agent, IP, and set a tracking cookie for anonymous profiling.
    """
    set_new_cookie = False
    # 1. Resolve or set tracking cookie
    if not visitor_id:
        import uuid
        visitor_id = f"px_visitor_{uuid.uuid4().hex[:12]}"
        set_new_cookie = True

    # 2. Extract header metadata
    user_agent = request.headers.get("user-agent", "")
    
    device_type = "desktop"
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device_type = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_type = "tablet"

    # 3. Create the event payload
    message = {
        "user_id":      visitor_id,
        "event_type":   event,
        "category":     category,
        "brand":        brand,
        "price_range":  price_range,
        "product_name": product_name,
        "age_group":    "",
        "gender":       "",
        "city":         "",
        "state":        "",
        "country":      "India",
        "device_type":  device_type,
        "platform":     "web",
        "source":       "pixel",
    }

    # 4. Forward to ingestion
    published = False
    if kafka_ok and producer:
        try:
            producer.send(KAFKA_TOPIC, key=visitor_id, value=message)
            published = True
        except Exception:
            pass

    if not published:
        try:
            _direct_mysql_event(
                visitor_id, event, category, brand, price_range, product_name
            )
        except Exception:
            pass

    # 5. Return 1x1 transparent gif image response and attach cookie
    res = Response(content=TRANSPARENT_GIF, media_type="image/gif")
    if set_new_cookie:
        res.set_cookie(key="visitor_id", value=visitor_id, max_age=31536000, httponly=True)
    return res


@app.get("/recommend/{user_id}", tags=["Recommendations"])
def recommend_for_user(
    user_id: str,
    k: int = Query(10, ge=1, le=50, description="Number of recommendations"),
):
    """
    Personalised recommendations for a user with purchase/browse history.

    1. Reads user's top interest from MySQL interest_profiles table
       (the same table kafka/consumer.py writes to)
    2. Checks Redis cache (< 5ms if hit)
    3. If cache miss: runs hybrid similarity model with time-decay
    4. Filters suppressed items (recently purchased / dismissed)
    5. Caches result for 1 hour
    """
    t0 = time.time()

    # Read top interest from MySQL
    interest = engine.get_top_interest_from_mysql(user_id)
    if not interest:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No profile found for '{user_id}'. "
                f"Run kafka/producer.py to stream events, or POST /event."
            )
        )

    cat   = interest["category"]
    brand = interest["brand"]
    price = interest["price_range"]
    days  = interest["days_ago"]

    # Cache check
    cached = cache.get_recs(cat, brand, price, days, k)
    if cached:
        return {
            "user_id":       user_id,
            "core_id":       interest["core_id"],
            "source":        "cached",
            "model":         engine.model_label,
            "top_interest":  interest,
            "recommendations": cached,
            "latency_ms":    round((time.time() - t0) * 1000, 2),
        }

    # Get suppressed items from MySQL
    suppressed = engine.get_suppressed_items(user_id)

    # Run hybrid model
    recs = engine.recommend(cat, brand, price, days, top_n=k,
                            suppressed=suppressed)

    cache.set_recs(cat, brand, price, days, k, recs)

    return {
        "user_id":         user_id,
        "core_id":         interest["core_id"],
        "source":          "personalised",
        "model":           engine.model_label,
        "top_interest":    interest,
        "recommendations": recs,
        "total":           len(recs),
        "latency_ms":      round((time.time() - t0) * 1000, 2),
    }


@app.get("/recommend/cold/{category}", tags=["Recommendations"])
def cold_start_recommend(
    category: str,
    brand:    Optional[str] = Query(None),
    price:    Optional[str] = Query("unknown"),
    k:        int           = Query(10, ge=1, le=50),
):
    """
    Cold-start recommendations — no user history needed.
    Provide a category and optionally a brand/price hint.
    """
    t0 = time.time()
    if not brand:
        brands = engine.brands(category)
        brand  = brands[0] if brands else "unknown"

    recs = engine.recommend(category, brand, price or "unknown",
                            days_ago=0, top_n=k)
    return {
        "source":          "cold_start",
        "category":        category,
        "brand_hint":      brand,
        "model":           engine.model_label,
        "recommendations": recs,
        "total":           len(recs),
        "latency_ms":      round((time.time() - t0) * 1000, 2),
    }


@app.get("/profile/{user_id}", tags=["Profiles"])
def get_profile(user_id: str):
    """
    Full Epsilon-style 360 profile from MySQL.
    Shows all interest profiles, suppression windows, interaction counts.
    """
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Resolve user_id → core_id
        cursor.execute("""
            SELECT core_id FROM identities
            WHERE identifier_type = 'user_id' AND identifier_value = %s
            LIMIT 1
        """, (str(user_id),))
        row = cursor.fetchone()
        if not row:
            cursor.close(); conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"User '{user_id}' not found in MySQL."
            )

        core_id = row["core_id"]

        # All identities
        cursor.execute("""
            SELECT identifier_type, identifier_value, created_at
            FROM identities WHERE core_id = %s
        """, (core_id,))
        identities = cursor.fetchall()

        # All interest profiles
        cursor.execute("""
            SELECT main_category, brand, price_range,
                   interest_score, browse_score, purchase_score,
                   engagement_score, browse_count, cart_count,
                   purchase_count, dismiss_count, total_spent,
                   last_purchased, suppress_until, updated_at
            FROM interest_profiles
            WHERE core_id = %s
            ORDER BY interest_score DESC
        """, (core_id,))
        profiles = cursor.fetchall()

        # Total interactions
        cursor.execute(
            "SELECT COUNT(*) as total FROM interactions WHERE core_id = %s",
            (core_id,)
        )
        total_events = cursor.fetchone()["total"]

        # Demographics
        cursor.execute(
            "SELECT * FROM user_demographics WHERE core_id = %s",
            (core_id,)
        )
        demographics = cursor.fetchone()

        cursor.close(); conn.close()

        # Serialise datetimes
        for p in profiles:
            for k in ["last_purchased", "suppress_until", "updated_at"]:
                if p.get(k): p[k] = str(p[k])
        for i in identities:
            if i.get("created_at"): i["created_at"] = str(i["created_at"])
        if demographics:
            for k, v in demographics.items():
                if hasattr(v, "isoformat"): demographics[k] = str(v)

        return {
            "user_id":         user_id,
            "core_id":         core_id,
            "total_events":    total_events,
            "identities":      identities,
            "interest_profiles": profiles,
            "demographics":    demographics or {},
            "profile_count":   len(profiles),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/catalog/categories", tags=["Catalog"])
def list_categories():
    cats = engine.categories()
    return {"count": len(cats), "categories": cats}


@app.get("/catalog/brands", tags=["Catalog"])
def list_brands(
    category: Optional[str] = Query(None)
):
    brands = engine.brands(category)
    return {"count": len(brands), "category": category or "all",
            "brands": brands[:100]}


@app.get("/metrics", tags=["General"])
def live_metrics():
    """
    Run a live 100-product evaluation sample.
    Returns P@K, R@K, F1@K, NDCG@K.
    Takes ~5 seconds — used to verify model health.
    """
    t0       = time.time()
    products = engine.products
    price_tiers = engine.price_tiers

    def price_ok(u, p, tol=1):
        try: return abs(price_tiers.index(u) - price_tiers.index(p)) <= tol
        except ValueError: return True

    def ndcg(rel):
        dcg  = sum(r / math.log2(i+2) for i, r in enumerate(rel))
        idcg = sum(r / math.log2(i+2) for i, r in enumerate(sorted(rel, reverse=True)))
        return dcg / idcg if idcg > 0 else 0.0

    K_VALUES = [1, 3, 5, 10]
    results  = {k: {"pk": [], "rk": [], "ndcg": []} for k in K_VALUES}

    sample = products.sample(min(100, len(products)),
                             random_state=int(time.time()) % 100)
    for _, row in sample.iterrows():
        cat   = str(row["main_category"])
        brand = str(row["brand"])
        price = str(row["price_range"])
        recs  = engine.recommend(cat, brand, price, days_ago=0, top_n=10)
        if not recs: continue

        for k in K_VALUES:
            top_k = recs[:k]
            hits  = sum(
                1 for r in top_k
                if r["main_category"] == cat and price_ok(price, r["price_range"])
            )
            total_rel = len(products[
                (products["main_category"] == cat) &
                products["price_range"].apply(
                    lambda p: price_ok(price, str(p))
                )
            ])
            pk  = hits / k
            rk  = hits / min(total_rel, k) if total_rel > 0 else 0
            rel = [
                1 if r["main_category"] == cat and price_ok(price, r["price_range"])
                else 0 for r in top_k
            ]
            results[k]["pk"].append(pk)
            results[k]["rk"].append(rk)
            results[k]["ndcg"].append(ndcg(rel))

    metrics = {}
    for k in K_VALUES:
        pk = float(np.mean(results[k]["pk"]))  if results[k]["pk"]   else 0
        rk = float(np.mean(results[k]["rk"]))  if results[k]["rk"]   else 0
        f1 = 2*pk*rk/(pk+rk)                   if (pk+rk) > 0       else 0
        nd = float(np.mean(results[k]["ndcg"])) if results[k]["ndcg"] else 0
        metrics[f"K{k}"] = {
            "precision": round(pk*100, 1),
            "recall":    round(rk*100, 1),
            "f1":        round(f1*100, 1),
            "ndcg":      round(nd*100, 1),
        }

    return {
        "model":       engine.model_label,
        "sample_size": len(sample),
        "metrics":     metrics,
        "latency_ms":  round((time.time() - t0) * 1000, 2),
    }


# ── MySQL direct fallback (when Kafka is unavailable) ──────────
SCORE_WEIGHTS = {
    "view": 0.5, "search": 0.3, "cart": 1.0,
    "wishlist": 0.8, "purchase": 2.0,
    "ignore": -0.3, "dismiss": -1.0,
}

def _direct_mysql_event(
    user_id: str, event_type: str, category: str,
    brand: str, price_range: str, product_name: str = "",
):
    """
    Write event directly to MySQL — mirrors what consumer.py does.
    Only called when Kafka is unavailable.
    """
    import uuid
    from datetime import datetime, timedelta

    try:
        conn   = get_db()
        cursor = conn.cursor()

        # Resolve or create identity
        cursor.execute("""
            SELECT core_id FROM identities
            WHERE identifier_type='user_id' AND identifier_value=%s
        """, (user_id,))
        row = cursor.fetchone()

        if row:
            core_id = row[0]
        else:
            core_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO users (core_id) VALUES (%s)", (core_id,))
            cursor.execute("""
                INSERT INTO identities (core_id, identifier_type, identifier_value)
                VALUES (%s, 'user_id', %s)
            """, (core_id, user_id))

        # Log interaction
        cursor.execute("""
            INSERT INTO interactions
              (core_id, event_type, main_category, brand,
               price_range, product_name, source)
            VALUES (%s,%s,%s,%s,%s,%s,'api_direct')
        """, (core_id, event_type, category, brand,
              price_range, product_name or None))

        # Update interest profile
        weight = SCORE_WEIGHTS.get(event_type, 0)
        cursor.execute("""
            SELECT profile_id, interest_score, browse_count,
                   purchase_count
            FROM interest_profiles
            WHERE core_id=%s AND main_category=%s AND brand=%s
        """, (core_id, category, brand))
        existing = cursor.fetchone()

        suppress_until = None
        if event_type == "purchase":
            suppress_until = datetime.now() + timedelta(days=90)
        elif event_type == "dismiss":
            suppress_until = datetime.now() + timedelta(days=7)

        if existing:
            pid, score, b_cnt, p_cnt = existing
            cursor.execute("""
                UPDATE interest_profiles
                SET interest_score  = %s,
                    browse_count    = %s,
                    purchase_count  = %s,
                    suppress_until  = %s,
                    updated_at      = NOW()
                WHERE profile_id = %s
            """, (
                max(0, score + weight),
                b_cnt + (1 if event_type == "view" else 0),
                p_cnt + (1 if event_type == "purchase" else 0),
                suppress_until, pid,
            ))
        else:
            cursor.execute("""
                INSERT INTO interest_profiles
                  (core_id, main_category, brand, price_range,
                   interest_score, browse_count, purchase_count,
                   suppress_until)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                core_id, category, brand, price_range,
                max(0, weight),
                1 if event_type == "view" else 0,
                1 if event_type == "purchase" else 0,
                suppress_until,
            ))

        conn.commit()
        cursor.close(); conn.close()

    except Exception as e:
        print(f"[MySQL Direct] Error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=5000, reload=True)
