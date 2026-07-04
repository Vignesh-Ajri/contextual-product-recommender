import pytest
import sys
import importlib.util
from unittest.mock import patch, MagicMock

# Dynamically load the consumer script from file path to bypass library shadow conflict
spec = importlib.util.spec_from_file_location("consumer", "kafka/consumer.py")
consumer_module = importlib.util.module_from_spec(spec)
sys.modules["consumer"] = consumer_module
spec.loader.exec_module(consumer_module)

@patch("consumer.get_db_connection")
@patch("consumer.resolve_identity")
@patch("consumer.save_interaction")
@patch("consumer.update_demographics")
@patch("consumer.update_interest_profile")
def test_end_to_end_event_processing(
    mock_update_profile,
    mock_update_demographics,
    mock_save_interaction,
    mock_resolve_identity,
    mock_get_db_connection
):
    # 1. Setup mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db_connection.return_value = mock_conn
    mock_resolve_identity.return_value = "core_user_999"
    
    # 2. Simulate raw incoming event payload
    raw_event = {
        "user_id": "raw_user_123",
        "event_type": "purchase",
        "main_category": "appliances",
        "brand": "lg",
        "price_range": "medium",
        "product_name": "Washing Machine",
        "device_id": "device_xyz",
        "ip_address": "192.168.1.1",
        "email": "user@example.com"
    }
    
    # 3. Process the event (blackbox entry point)
    consumer_module.process_event(raw_event)
    
    # 4. Verify all processing pipeline steps were executed sequentially
    mock_get_db_connection.assert_called()
    # Note: device_id and email are not tracked/cleaned by validate_event, so they fall back to empty strings
    mock_resolve_identity.assert_called_once_with(
        mock_cursor, "raw_user_123", "", "192.168.1.1", "", ""
    )
    mock_save_interaction.assert_called_once()
    mock_update_demographics.assert_called_once()
    mock_update_profile.assert_called_once()
    mock_conn.commit.assert_called_once()
