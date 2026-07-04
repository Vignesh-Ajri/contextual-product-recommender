import pytest
from unittest.mock import patch, MagicMock

def test_welcome_endpoint(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert "CPRP" in response.json()["project"]

def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "mysql" in data
    assert "redis" in data
    assert "kafka" in data

@patch("api.app.producer")
@patch("api.app.kafka_ok", True)
def test_post_event_success_kafka(mock_producer, test_client):
    event_payload = {
        "user_id": "test_user_123",
        "event_type": "view",
        "category": "electronics",
        "brand": "samsung"
    }
    response = test_client.post("/event", json=event_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["delivery"] == "kafka"
    mock_producer.send.assert_called_once()

@patch("api.app.get_db")
@patch("api.app.kafka_ok", False)
def test_post_event_success_db_fallback(mock_get_db, test_client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    event_payload = {
        "user_id": "test_user_123",
        "event_type": "view",
        "category": "electronics",
        "brand": "samsung"
    }
    response = test_client.post("/event", json=event_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["delivery"] == "mysql_direct"
    assert mock_cursor.execute.called

def test_post_event_invalid(test_client):
    # Missing required 'category' field
    event_payload = {
        "user_id": "test_user_123",
        "event_type": "view"
    }
    response = test_client.post("/event", json=event_payload)
    assert response.status_code == 422

@patch("api.app.producer")
@patch("api.app.kafka_ok", True)
def test_tracking_pixel(mock_producer, test_client):
    response = test_client.get("/api/v1/pixel.gif?event=view&category=electronics&brand=samsung")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/gif"
    assert "visitor_id" in response.cookies
    assert mock_producer.send.called

