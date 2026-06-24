import json, os, hashlib
from dotenv import load_dotenv
load_dotenv()

try:
    import redis
    _client = redis.Redis(
        host=os.getenv("REDIS_HOST","localhost"),
        port=int(os.getenv("REDIS_PORT",6379)),
        db=int(os.getenv("REDIS_DB",0)),
        decode_responses=True,
        socket_connect_timeout=2, socket_timeout=2,
    )
    _client.ping()
    REDIS_OK = True
    print(f"[Cache] Redis connected")
except Exception as e:
    _client  = None
    REDIS_OK = False
    print(f"[Cache] Redis unavailable ({e})")

TTL_RECS, TTL_PROFILE = 3600, 1800

def _rec_key(cat,brand,price,days,k):
    return "rec:" + hashlib.md5(f"{cat}|{brand}|{price}|{days}|{k}".encode()).hexdigest()

def get_recs(cat,brand,price,days,k):
    if not REDIS_OK: return None
    try:
        d = _client.get(_rec_key(cat,brand,price,days,k))
        return json.loads(d) if d else None
    except: return None

def set_recs(cat,brand,price,days,k,recs):
    if not REDIS_OK: return
    try: _client.setex(_rec_key(cat,brand,price,days,k), TTL_RECS, json.dumps(recs))
    except: pass

def invalidate_user(user_id):
    if not REDIS_OK: return 0
    try:
        keys = _client.keys(f"profile:{user_id}*")
        return _client.delete(*keys) if keys else 0
    except: return 0

def cache_stats():
    if not REDIS_OK: return {"available": False}
    try:
        info = _client.info("stats")
        return {
            "available": True,
            "hits":   info.get("keyspace_hits",0),
            "misses": info.get("keyspace_misses",0),
            "keys":   _client.dbsize(),
        }
    except Exception as e: return {"available": False, "error": str(e)}
