import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Mock environmental variables before importing the app
@pytest.fixture(scope="session", autouse=True)
def mock_env(monitoring_monkeypatch=None):
    with patch.dict("os.environ", {
        "DB_HOST": "localhost",
        "DB_PORT": "3307",
        "DB_USER": "root",
        "DB_PASSWORD": "password",
        "DB_NAME": "test_db",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_TOPIC_EVENTS": "test_events"
    }):
        yield

@pytest.fixture
def mock_db():
    with patch("mysql.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn, mock_cursor

@pytest.fixture
def mock_redis():
    with patch("redis.Redis") as mock_redis_class:
        mock_redis_inst = MagicMock()
        mock_redis_class.return_value = mock_redis_inst
        yield mock_redis_inst

@pytest.fixture
def mock_kafka():
    with patch("kafka.KafkaProducer") as mock_producer_class:
        mock_producer_inst = MagicMock()
        mock_producer_class.return_value = mock_producer_inst
        yield mock_producer_inst

@pytest.fixture
def test_client():
    # Lazy import to ensure env mocks are in place
    with patch("kafka.KafkaProducer"), \
         patch("mysql.connector.connect"), \
         patch("redis.Redis") as mock_redis_class:
        
        # Make Redis look connected
        mock_redis_inst = MagicMock()
        mock_redis_inst.ping.return_value = True
        mock_redis_class.return_value = mock_redis_inst
        
        from api.app import app
        with TestClient(app) as client:
            yield client
