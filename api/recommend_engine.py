# ============================================================
# CPRP — Recommendation Engine
# ============================================================

import os
import math
import numpy as np
import pandas as pd
import joblib
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

ML_DIR = os.path.join(os.path.dirname(__file__), "..", "ml")

def _load(name):
    return joblib.load(os.path.join(ML_DIR, name))

def _load_fallback(primary, fallback):
    try:
        obj = _load(primary)
        return obj, primary
    except FileNotFoundError:
        obj = _load(fallback)
        return obj, fallback

# ── DB config from .env ───────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 3307)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


class RecommendEngine:
    """
    Loads model artifacts once at startup.
    Reads user interest signals from MySQL at recommendation time.
    """

    def __init__(self):
        print("[Engine] Loading model artifacts...")

        # Prefer hybrid — fall back to BM25
        self.sim_matrix, self.sim_source = _load_fallback(
            "hybrid_v2_sim.pkl", "bm25_sim.pkl"
        )
        print(f"[Engine] Similarity  : {self.sim_source}  {self.sim_matrix.shape}")

        self.products     = pd.read_csv(os.path.join(ML_DIR, "products.csv"))
        self.cat_hl       = _load("category_half_life.pkl")
        self.cat_fallback = _load("category_fallback.pkl")
        self.price_tiers  = _load("price_tier_order.pkl")

        # Build product_key lookup for fast index resolution
        self.products["product_key"] = (
            self.products["main_category"].str.lower() + "::" +
            self.products["brand"].str.lower()
        )
        self.key_to_idx = {
            k: i for i, k in enumerate(self.products["product_key"])
        }

        try:
            w = _load("hybrid_weights.pkl")
            self.model_label = (
                f"Hybrid — BM25({w['bm25']}) "
                f"ALS({w['als']}) "
                f"Embed({w['embed']})"
            )
        except FileNotFoundError:
            self.model_label = "BM25 content-based"

        print(f"[Engine] Model       : {self.model_label}")
        print(f"[Engine] Products    : {len(self.products):,}")
        print("[Engine] Ready.")

    # ── MySQL helpers ─────────────────────────────────────────

    def get_top_interest_from_mysql(self, user_id: str) -> dict | None:
        """
        Resolve user_id → core_id → top interest_profile from MySQL.

        Reads from the same tables kafka/consumer.py writes to:
          identities       → resolves user_id to core_id
          interest_profiles → finds highest-scored unsuppressed interest

        Returns dict with category, brand, price_range, interest_score,
        days_since_last_event — or None if user not found.
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)

            # Step 1: resolve user_id → core_id via identities table
            cursor.execute("""
                SELECT core_id FROM identities
                WHERE identifier_type = 'user_id'
                  AND identifier_value = %s
                LIMIT 1
            """, (str(user_id),))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                return None

            core_id = row["core_id"]

            # Step 2: get top interest (highest score, not suppressed)
            cursor.execute("""
                SELECT
                    main_category,
                    brand,
                    price_range,
                    interest_score,
                    browse_count,
                    purchase_count,
                    suppress_until,
                    updated_at
                FROM interest_profiles
                WHERE core_id = %s
                  AND (suppress_until IS NULL OR suppress_until < NOW())
                ORDER BY interest_score DESC
                LIMIT 1
            """, (core_id,))
            profile = cursor.fetchone()

            cursor.close()
            conn.close()

            if not profile:
                return None

            # Calculate days since last interaction for time-decay
            from datetime import datetime
            updated = profile.get("updated_at")
            if updated:
                days_ago = max(0, (datetime.now() - updated).days)
            else:
                days_ago = 0

            return {
                "core_id":       core_id,
                "category":      profile["main_category"],
                "brand":         profile["brand"],
                "price_range":   profile["price_range"],
                "score":         float(profile["interest_score"]),
                "browse_count":  profile["browse_count"],
                "purchase_count":profile["purchase_count"],
                "days_ago":      days_ago,
            }

        except Exception as e:
            print(f"[Engine] MySQL error: {e}")
            return None

    def get_suppressed_items(self, user_id: str) -> set:
        """
        Return set of (category, brand) tuples that are currently
        suppressed for this user (recently purchased or dismissed).
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT i.core_id FROM identities i
                WHERE i.identifier_type = 'user_id'
                  AND i.identifier_value = %s
                LIMIT 1
            """, (str(user_id),))
            row = cursor.fetchone()
            if not row:
                cursor.close(); conn.close()
                return set()

            core_id = row["core_id"]
            cursor.execute("""
                SELECT main_category, brand
                FROM interest_profiles
                WHERE core_id = %s
                  AND suppress_until IS NOT NULL
                  AND suppress_until > NOW()
            """, (core_id,))
            suppressed = {
                (r["main_category"], r["brand"])
                for r in cursor.fetchall()
            }
            cursor.close(); conn.close()
            return suppressed

        except Exception:
            return set()

    # ── Core recommendation method ────────────────────────────

    def recommend(
        self,
        category:    str,
        brand:       str,
        price_range: str  = "unknown",
        days_ago:    int  = 0,
        top_n:       int  = 10,
        suppressed:  set  = None,
    ) -> list[dict]:
        """
        Return top_n recommendations for a (category, brand) anchor.
        Used by both personalised and cold-start endpoints.
        """
        if suppressed is None:
            suppressed = set()

        # Find anchor in catalog
        match = self.products[
            (self.products["main_category"] == category) &
            (self.products["brand"] == brand)
        ]
        if len(match) == 0:
            match = self.products[self.products["main_category"] == category]
        if len(match) == 0:
            return []

        hl     = self.cat_hl.get(category, 30)
        decay  = math.exp(-0.693 * days_ago / hl) if days_ago > 0 else 1.0
        idx    = match.index[0]
        scores = self.sim_matrix[idx].copy() * decay

        raw  = []
        seen = set()

        for i in np.argsort(scores)[::-1]:
            p  = self.products.iloc[i]
            pc = str(p["main_category"])
            pb = str(p["brand"])
            pp = str(p["price_range"])

            if pc == category and pb == brand:
                continue
            if (pc, pb) in suppressed:
                continue
            if price_range != "unknown" and not self._price_ok(price_range, pp):
                continue
            if (pc, pb) in seen:
                continue

            seen.add((pc, pb))
            raw.append({
                "main_category": pc,
                "brand":         pb,
                "price_range":   pp,
                "score":         round(float(scores[i]), 4),
            })
            if len(raw) >= top_n * 4:
                break

        # Cross-category fallback when same-cat results are sparse
        same_cat = sum(1 for r in raw if r["main_category"] == category)
        if same_cat < top_n // 2:
            for fb_cat in self.cat_fallback.get(category, []):
                for _, fp in self.products[
                    self.products["main_category"] == fb_cat
                ].iterrows():
                    key = (str(fp["main_category"]), str(fp["brand"]))
                    if key not in seen and key not in suppressed:
                        seen.add(key)
                        fb_score = (
                            float(self.sim_matrix[idx][fp.name]) * decay * 0.85
                        )
                        raw.append({
                            "main_category": str(fp["main_category"]),
                            "brand":         str(fp["brand"]),
                            "price_range":   str(fp["price_range"]),
                            "score":         round(fb_score, 4),
                        })
                if len(raw) >= top_n * 4:
                    break

        raw.sort(key=lambda x: -x["score"])
        diversified = self._diversify(raw)[:top_n]

        for rank, rec in enumerate(diversified, start=1):
            rec["rank"] = rank

        return diversified

    # ── Helpers ───────────────────────────────────────────────

    def _price_ok(self, user_tier: str, prod_tier: str, tol: int = 1) -> bool:
        try:
            return abs(
                self.price_tiers.index(user_tier) -
                self.price_tiers.index(prod_tier)
            ) <= tol
        except ValueError:
            return True

    def _diversify(self, results: list, max_per_brand: int = 2) -> list:
        seen = {}
        out  = []
        for r in results:
            c = seen.get(r["brand"], 0)
            if c < max_per_brand:
                out.append(r)
                seen[r["brand"]] = c + 1
        return out

    def categories(self) -> list[str]:
        return sorted(self.products["main_category"].unique().tolist())

    def brands(self, category: str | None = None) -> list[str]:
        if category:
            return sorted(
                self.products[
                    self.products["main_category"] == category
                ]["brand"].unique().tolist()
            )
        return sorted(self.products["brand"].unique().tolist())
