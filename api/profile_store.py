# Kept for cold-start fallback — main profiles now live in MySQL
import math, time

EVENT_WEIGHTS = {
    "purchase":2.0,"cart":1.0,"wishlist":0.8,
    "view":0.5,"search":0.3,"ignore":-0.3,"dismiss":-1.0,
}
SUPPRESS_THRESHOLD = -1.5
DEFAULT_HL = 30

class ProfileStore:
    def __init__(self, category_half_life: dict):
        self._hl       = category_half_life
        self._profiles = {}
        self._blocked  = {}

    def record_event(self, user_id, event_type, category, brand, price_range):
        now    = time.time()
        weight = EVENT_WEIGHTS.get(event_type, 0.0)
        hl     = self._hl.get(category, DEFAULT_HL)
        if user_id not in self._profiles: self._profiles[user_id] = {}
        p   = self._profiles[user_id]
        key = f"{category}::{brand}"
        if key not in p:
            p[key] = {"score":0.0,"category":category,"brand":brand,
                      "price_range":price_range,"last_event":now,"event_count":0}
        e = p[key]
        days = (now - e["last_event"]) / 86400.0
        e["score"]       = max(0.0, e["score"] * math.exp(-0.693*days/hl))
        e["score"]       = max(0.0, e["score"] + weight)
        e["last_event"]  = now
        e["event_count"] += 1
        e["price_range"] = price_range
        if e["score"] <= SUPPRESS_THRESHOLD:
            if user_id not in self._blocked: self._blocked[user_id] = set()
            self._blocked[user_id].add((category,brand))
        return self.get_profile(user_id)

    def get_profile(self, user_id):
        if user_id not in self._profiles: return None
        now  = time.time()
        aged = []
        for key, e in self._profiles[user_id].items():
            hl   = self._hl.get(e["category"], DEFAULT_HL)
            days = (now - e["last_event"]) / 86400.0
            live = max(0.0, e["score"] * math.exp(-0.693*days/hl))
            aged.append({"category":e["category"],"brand":e["brand"],
                         "price_range":e["price_range"],"score":round(live,4),
                         "event_count":e["event_count"]})
        aged.sort(key=lambda x:-x["score"])
        return {
            "user_id":      user_id,
            "top_category": aged[0]["category"]    if aged else None,
            "top_brand":    aged[0]["brand"]        if aged else None,
            "top_price":    aged[0]["price_range"]  if aged else None,
            "top_score":    aged[0]["score"]        if aged else 0.0,
            "interests":    aged[:10],
        }

    def is_blocked(self, user_id, category, brand):
        return (category,brand) in self._blocked.get(user_id, set())

    def user_count(self): return len(self._profiles)
