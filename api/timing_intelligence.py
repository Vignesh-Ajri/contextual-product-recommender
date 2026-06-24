# ============================================================
# CPRP — Timing Intelligence Module
# File: api/timing_intelligence.py
#
# Called from kafka/consumer.py on every event to track
# engagement patterns per user per hour/day.
# ============================================================
from datetime import datetime

def update_engagement_pattern(cursor, core_id, event_time=None):
    """Update hourly engagement pattern for this user."""
    if event_time is None: event_time = datetime.now()
    try:
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time.replace(" ","T"))
    except: event_time = datetime.now()
    hour = event_time.hour
    dow  = event_time.weekday()  # 0=Mon, 6=Sun
    cursor.execute("""
        INSERT INTO engagement_patterns (core_id, hour_of_day, day_of_week, event_count, last_seen)
        VALUES (%s, %s, %s, 1, NOW())
        ON DUPLICATE KEY UPDATE
            event_count = event_count + 1,
            last_seen   = NOW(),
            updated_at  = NOW()
    """, (core_id, hour, dow))

def update_identity_confidence(cursor, core_id, matched_signals: list):
    """
    Update identity confidence score based on signals matched.
    Signals: email, phone, device_id, session, behavior
    Score: each signal adds weight
    """
    signal_weights = {
        "email":    0.40,
        "phone":    0.35,
        "device_id":0.15,
        "session":  0.05,
        "behavior": 0.05,
    }
    score = sum(signal_weights.get(s, 0.05) for s in matched_signals)
    score = min(1.0, round(score, 3))
    signals_str = ",".join(matched_signals)
    res_type = "deterministic" if any(s in matched_signals for s in ["email","phone"]) else "probabilistic"
    cursor.execute("""
        INSERT INTO identity_confidence (core_id, match_signals, confidence_score, resolution_type)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            match_signals    = %s,
            confidence_score = %s,
            resolution_type  = %s,
            updated_at       = NOW()
    """, (core_id, signals_str, score, res_type,
          signals_str, score, res_type))
    return score