"""
Tests for the kline_data_processor in the Data Ingestion Service main module.
"""
import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, call # call for checking multiple calls
from decimal import Decimal

from backend.data_ingestion_service.main import kline_data_processor
from backend.app.models import Kline # For constructing expected Kline object if needed
from backend.app.config import Settings
from sqlalchemy.dialects.postgresql import insert as pg_insert # To check statement type
from sqlalchemy.exc import SQLAlchemyError
import redis # For redis.exceptions.RedisError

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_kline_data_from_ws():
    """Provides a sample kline data dictionary as received from BinanceWebSocketManager."""
    return {
        "symbol": "BTCUSDT", "timeframe": "1m", "open_time": 1678886400000,
        "open_price": "20000.0", "high_price": "20600.0", "low_price": "19900.0", 
        "close_price": "20500.0", "volume": "1000.0", "is_closed": True,
        "close_time": 1678886459999, "quote_asset_volume": "20250000.0",
        "number_of_trades": 100, "taker_buy_base_asset_volume": "500.0",
        "taker_buy_quote_asset_volume": "10125000.0"
        # Raw Kline data may have more fields, these are the ones used by processor
    }

@pytest.fixture
def mock_redis_client_for_processor():
    client = MagicMock(spec=redis.Redis)
    client.zadd = MagicMock(return_value=1) # Assume 1 element added
    client.zremrangebyrank = MagicMock(return_value=0) # Assume nothing trimmed for simplicity here
    client.publish = MagicMock(return_value=1) # Assume 1 client received
    return client

@pytest.fixture
def mock_db_session_for_processor():
    session = MagicMock()
    session.execute = MagicMock() # Result of execute can be more complex for on_conflict
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session

@pytest.fixture
def mock_db_session_factory_for_processor(mock_db_session_for_processor):
    factory = MagicMock(return_value=mock_db_session_for_processor)
    return factory

@pytest.fixture
def mock_settings_for_processor():
    return Settings(MAX_KLINES_IN_REDIS=100) # Example setting

async def test_kline_processor_success_path(
    mock_kline_data_from_ws,
    mock_redis_client_for_processor,
    mock_db_session_factory_for_processor,
    mock_db_session_for_processor, # To assert calls on the session itself
    mock_settings_for_processor
):
    """Test the success path: DB save, Redis cache update, Redis publish."""
    
    with patch("backend.data_ingestion_service.main.settings", mock_settings_for_processor):
        await kline_data_processor(
            mock_kline_data_from_ws,
            mock_redis_client_for_processor,
            mock_db_session_factory_for_processor
        )

    # 1. DB Assertions
    mock_db_session_factory_for_processor.assert_called_once() # Factory was called to get a session
    # Check that execute was called with an insert statement
    assert mock_db_session_for_processor.execute.call_count == 1
    executed_statement = mock_db_session_for_processor.execute.call_args[0][0]
    # Check if it's a SQLAlchemy insert statement (more specific checks are harder without deep SQLAlchemy mocking)
    # For PostgreSQL, it should be `sqlalchemy.dialects.postgresql.dml.Insert`
    assert "INSERT INTO klines" in str(executed_statement.compile(dialect=pg_insert(Kline).dialect)).upper()
    assert "ON CONFLICT (symbol, timeframe, open_time) DO NOTHING" in str(executed_statement.compile(dialect=pg_insert(Kline).dialect)).upper()
    mock_db_session_for_processor.commit.assert_called_once()
    mock_db_session_for_processor.rollback.assert_not_called()
    mock_db_session_for_processor.close.assert_called_once()

    # 2. Redis Cache Assertions
    redis_key = f"klines:{mock_kline_data_from_ws['symbol']}:{mock_kline_data_from_ws['timeframe']}"
    expected_redis_score = mock_kline_data_from_ws['open_time']
    # Kline data for Redis is a JSON string of the original dict, with Decimals as strings
    expected_redis_member_dict = {
        k: str(v) if isinstance(v, Decimal) else v 
        for k, v in mock_kline_data_from_ws.items()
    }
    # The processor maps to Kline model first, then converts that to dict for JSON. So field names might differ slightly if mapping changes.
    # Let's check the call to zadd more generically first.
    mock_redis_client_for_processor.zadd.assert_called_once()
    zadd_args = mock_redis_client_for_processor.zadd.call_args[0]
    assert zadd_args[0] == redis_key
    # zadd_args[1] is the mapping {member: score, ...}
    # The member is a JSON string. Score is open_time.
    # Example: ({json_string_of_kline: open_time_int})
    # We expect only one kline to be added here.
    added_member_json_str = list(zadd_args[1].keys())[0]
    added_member_score = list(zadd_args[1].values())[0]
    assert added_member_score == expected_redis_score
    # Parse the JSON string from the zadd call to check its contents
    added_member_dict_actual = json.loads(added_member_json_str)
    assert added_member_dict_actual["symbol"] == mock_kline_data_from_ws["symbol"]
    assert added_member_dict_actual["open_time"] == mock_kline_data_from_ws["open_time"]
    assert float(added_member_dict_actual["open_price"]) == float(mock_kline_data_from_ws["open_price"]) # Compare as float due to string source

    # Check trim call
    # zremrangebyrank klines:SYMBOL:TIMEFRAME 0 -(MAX_KLINES_IN_REDIS + 1)
    mock_redis_client_for_processor.zremrangebyrank.assert_called_once_with(
        redis_key, 0, -(mock_settings_for_processor.MAX_KLINES_IN_REDIS + 1)
    )

    # 3. Redis Pub/Sub Assertions
    pubsub_channel = f"kline_updates:{mock_kline_data_from_ws['symbol']}:{mock_kline_data_from_ws['timeframe']}"
    mock_redis_client_for_processor.publish.assert_called_once()
    publish_args = mock_redis_client_for_processor.publish.call_args[0]
    assert publish_args[0] == pubsub_channel
    # The published message should be the same JSON string as added to the cache member.
    published_member_dict_actual = json.loads(publish_args[1])
    assert published_member_dict_actual["symbol"] == mock_kline_data_from_ws["symbol"]
    assert published_member_dict_actual["open_time"] == mock_kline_data_from_ws["open_time"]

async def test_kline_processor_db_failure(
    mock_kline_data_from_ws,
    mock_redis_client_for_processor,
    mock_db_session_factory_for_processor,
    mock_db_session_for_processor,
    mock_settings_for_processor
):
    """Test that Redis operations are skipped if DB save fails."""
    mock_db_session_for_processor.execute.side_effect = SQLAlchemyError("DB Error")

    with patch("backend.data_ingestion_service.main.settings", mock_settings_for_processor):
        await kline_data_processor(
            mock_kline_data_from_ws,
            mock_redis_client_for_processor,
            mock_db_session_factory_for_processor
        )

    mock_db_session_for_processor.execute.assert_called_once()
    mock_db_session_for_processor.commit.assert_not_called()
    mock_db_session_for_processor.rollback.assert_called_once()
    mock_db_session_for_processor.close.assert_called_once()

    mock_redis_client_for_processor.zadd.assert_not_called()
    mock_redis_client_for_processor.zremrangebyrank.assert_not_called()
    mock_redis_client_for_processor.publish.assert_not_called()

async def test_kline_processor_redis_cache_failure(
    mock_kline_data_from_ws,
    mock_redis_client_for_processor,
    mock_db_session_factory_for_processor,
    mock_db_session_for_processor, # For DB success checks
    mock_settings_for_processor
):
    """Test that Pub/Sub still happens if Redis cache update (zadd) fails, but logs error."""
    mock_redis_client_for_processor.zadd.side_effect = redis.exceptions.RedisError("Cache Error")
    
    # We need to patch logger to check for error logs
    with patch("backend.data_ingestion_service.main.logger.error") as mock_logger_error:
        with patch("backend.data_ingestion_service.main.settings", mock_settings_for_processor):
            await kline_data_processor(
                mock_kline_data_from_ws,
                mock_redis_client_for_processor,
                mock_db_session_factory_for_processor
            )

    # DB should succeed
    mock_db_session_for_processor.execute.assert_called_once()
    mock_db_session_for_processor.commit.assert_called_once()

    # Redis cache (zadd) was called and failed
    mock_redis_client_for_processor.zadd.assert_called_once()
    # zremrangebyrank should still be called as it's in a separate try-except in the original code
    # (though logically it might be better if it also depended on zadd success)
    # Current code has trim in a separate try-block, so it *will* be called.
    mock_redis_client_for_processor.zremrangebyrank.assert_called_once()
    
    # Check that an error was logged for the zadd failure
    # mock_logger_error.assert_any_call(f"Error updating Redis cache for ...: Cache Error") # Exact message matching
    assert mock_logger_error.call_count > 0 # Check at least one error was logged for Redis cache
    # Verify that the error log contains relevant info
    found_cache_error_log = False
    for call_arg in mock_logger_error.call_args_list:
        if "Error updating Redis cache" in call_arg[0][0] and "Cache Error" in str(call_arg[0][1]):
            found_cache_error_log = True
            break
    assert found_cache_error_log, "Expected Redis cache error was not logged"

    # Pub/Sub should still be attempted and succeed
    mock_redis_client_for_processor.publish.assert_called_once()

async def test_kline_processor_redis_publish_failure(
    mock_kline_data_from_ws,
    mock_redis_client_for_processor,
    mock_db_session_factory_for_processor,
    mock_db_session_for_processor, # For DB/Cache success checks
    mock_settings_for_processor
):
    """Test that DB and Cache can succeed, but if Publish fails, an error is logged."""
    mock_redis_client_for_processor.publish.side_effect = redis.exceptions.RedisError("Publish Error")

    with patch("backend.data_ingestion_service.main.logger.error") as mock_logger_error:
        with patch("backend.data_ingestion_service.main.settings", mock_settings_for_processor):
            await kline_data_processor(
                mock_kline_data_from_ws,
                mock_redis_client_for_processor,
                mock_db_session_factory_for_processor
            )
    
    # DB and Cache should succeed
    mock_db_session_for_processor.execute.assert_called_once()
    mock_db_session_for_processor.commit.assert_called_once()
    mock_redis_client_for_processor.zadd.assert_called_once()
    mock_redis_client_for_processor.zremrangebyrank.assert_called_once()

    # Publish was called and failed
    mock_redis_client_for_processor.publish.assert_called_once()
    # Check for error log related to publish failure
    found_publish_error_log = False
    for call_arg in mock_logger_error.call_args_list:
        if "Error publishing kline to Redis Pub/Sub" in call_arg[0][0] and "Publish Error" in str(call_arg[0][1]):
            found_publish_error_log = True
            break
    assert found_publish_error_log, "Expected Redis publish error was not logged" 