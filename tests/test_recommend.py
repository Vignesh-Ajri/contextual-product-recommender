import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_engine_dependencies():
    with patch("api.recommend_engine._load") as mock_load, \
         patch("api.recommend_engine._load_fallback") as mock_fallback, \
         patch("api.recommend_engine.pd.read_csv") as mock_read_csv:
        
        # Mock products dataframe
        mock_df = pd.DataFrame({
            "main_category": ["electronics", "appliances", "electronics"],
            "brand": ["samsung", "lg", "apple"],
            "product_name": ["TV", "Fridge", "iPhone"],
            "price": [50000, 30000, 80000],
            "price_range": ["high", "medium", "high"]
        })
        mock_read_csv.return_value = mock_df
        
        # Mock similarity matrix (shape 3x3)
        mock_sim = np.array([
            [1.0, 0.2, 0.8],
            [0.2, 1.0, 0.1],
            [0.8, 0.1, 1.0]
        ])
        mock_fallback.return_value = (mock_sim, "hybrid_v2_sim.pkl")
        
        # Mock other dictionary lookups
        mock_load.side_effect = lambda name: {
            "category_half_life.pkl": {"electronics": 30, "appliances": 60},
            "category_fallback.pkl": {"electronics": "appliances"},
            "price_tier_order.pkl": ["low", "medium", "high"],
            "hybrid_weights.pkl": {"bm25": 0.4, "als": 0.4, "embed": 0.2}
        }.get(name, {})
        
        yield

@patch("api.recommend_engine.get_db")
def test_recommend_engine_logic(mock_get_db, mock_engine_dependencies):
    from api.recommend_engine import RecommendEngine
    
    # Initialize the engine
    engine = RecommendEngine()
    
    # Verify products size
    assert len(engine.products) == 3
    
    # Mock database lookup for user profile with sequential results
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # First call to fetchone (identities table): returns core_id
    # Second call to fetchone (interest_profiles table): returns user profile details
    mock_cursor.fetchone.side_effect = [
        {"core_id": "core_user_123"},
        {
            "main_category": "electronics",
            "brand": "samsung",
            "price_range": "high",
            "interest_score": 2.5,
            "browse_count": 5,
            "purchase_count": 0,
            "suppress_until": None,
            "updated_at": datetime.now()
        }
    ]
    
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn
    
    # Test resolving user interest from MySQL
    profile = engine.get_top_interest_from_mysql("user_123")
    assert profile is not None
    assert profile["category"] == "electronics"
    assert profile["brand"] == "samsung"
