import pytest
from unittest.mock import patch, MagicMock

def test_cache_key_generation():
    from api.cache import _rec_key
    key1 = _rec_key("electronics", "samsung", "high", 5, 10)
    key2 = _rec_key("electronics", "samsung", "high", 5, 10)
    key3 = _rec_key("electronics", "lg", "high", 5, 10)
    
    assert key1 == key2
    assert key1 != key3

@patch("api.cache.REDIS_OK", True)
@patch("api.cache._client")
def test_cache_get_and_set(mock_redis_client):
    from api.cache import get_recs, set_recs
    
    # Mock return value for get
    mock_redis_client.get.return_value = '["prod1", "prod2"]'
    
    recs = get_recs("electronics", "samsung", "high", 5, 10)
    assert recs == ["prod1", "prod2"]
    
    # Test set
    set_recs("electronics", "samsung", "high", 5, 10, ["prod1", "prod2"])
    mock_redis_client.setex.assert_called_once()

@patch("api.cache.REDIS_OK", True)
@patch("api.cache._client")
def test_invalidate_user(mock_redis_client):
    from api.cache import invalidate_user
    
    mock_redis_client.keys.return_value = ["profile:user1:key1", "profile:user1:key2"]
    mock_redis_client.delete.return_value = 2
    
    deleted = invalidate_user("user1")
    assert deleted == 2
    mock_redis_client.delete.assert_called_once_with("profile:user1:key1", "profile:user1:key2")
