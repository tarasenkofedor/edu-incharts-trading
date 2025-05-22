"""
Tests for the data API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timezone, timedelta

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

async def test_get_klines_invalid_symbol_timeframe(test_client: AsyncClient):
    """Test fetching klines with syntactically valid but likely non-existent symbol/timeframe."""
    # This test doesn't mock the database or Redis yet, so it relies on them being empty
    # or the specific symbol/timeframe not existing.
    # It primarily tests that the endpoint runs without server errors for a basic case.
    response = await test_client.get("/data/klines/NONEXISTENT/1min")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["klines"] == []
    assert response_data["backfill_status"] is None
    assert response_data["backfill_last_updated_ts"] is None

async def test_get_klines_with_limit(test_client: AsyncClient, override_get_db):
    """Test fetching klines with a limit, ensuring the override_get_db fixture is used."""
    # This test will use the in-memory SQLite DB provided by override_get_db.
    # We are not populating data yet, so it will also return empty.
    # The main purpose here is to ensure the test setup with DB override works.
    response = await test_client.get("/data/klines/BTCUSDT/1m?limit=10")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["klines"] == []
    # Further assertions would involve populating the mock DB and checking results.

async def test_get_klines_with_data_from_db(test_client: AsyncClient, db_session, override_get_db):
    """Test fetching klines from the database after populating it."""
    from backend.app.models import Kline
    from decimal import Decimal
    # import time # No longer using time.time()

    # Prepare mock data
    symbol = "TESTCOIN/USD"
    timeframe = "1h"
    # Use fixed base time for predictable timestamps
    base_dt = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    mock_klines_db = [
        Kline(
            symbol=symbol, timeframe=timeframe, open_time=base_dt - timedelta(hours=2),
            open_price=Decimal("100.0"), high_price=Decimal("105.0"), low_price=Decimal("99.0"), close_price=Decimal("102.0"),
            volume=Decimal("1000.0"), close_time=base_dt - timedelta(hours=2) + timedelta(minutes=59, seconds=59, milliseconds=999),
            quote_asset_volume=Decimal("100000.0"), number_of_trades=100,
            taker_buy_base_asset_volume=Decimal("500.0"), taker_buy_quote_asset_volume=Decimal("50000.0")
        ),
        Kline(
            symbol=symbol, timeframe=timeframe, open_time=base_dt - timedelta(hours=1),
            open_price=Decimal("102.0"), high_price=Decimal("108.0"), low_price=Decimal("101.0"), close_price=Decimal("107.0"),
            volume=Decimal("1500.0"), close_time=base_dt - timedelta(hours=1) + timedelta(minutes=59, seconds=59, milliseconds=999),
            quote_asset_volume=Decimal("153000.0"), number_of_trades=150,
            taker_buy_base_asset_volume=Decimal("700.0"), taker_buy_quote_asset_volume=Decimal("71400.0")
        ),
    ]

    db_session.add_all(mock_klines_db)
    db_session.commit()

    # Pre-calculate expected timestamps for assertions
    # Ensure ORM datetime attributes (which might be naive UTC for SQLite) are made aware before .timestamp()
    k0_orm_dt = mock_klines_db[0].open_time
    if k0_orm_dt.tzinfo is None:
        k0_orm_dt = k0_orm_dt.replace(tzinfo=timezone.utc)
    expected_kline0_open_time_ms = int(k0_orm_dt.timestamp() * 1000)

    k1_orm_dt = mock_klines_db[1].open_time
    if k1_orm_dt.tzinfo is None:
        k1_orm_dt = k1_orm_dt.replace(tzinfo=timezone.utc)
    expected_kline1_open_time_ms = int(k1_orm_dt.timestamp() * 1000)
    
    print(f"TEST CALC: expected_kline0_open_time_ms = {expected_kline0_open_time_ms}")
    print(f"TEST CALC: mock_klines_db[0].open_time (from ORM) = {mock_klines_db[0].open_time}")
    print(f"TEST CALC: expected_kline1_open_time_ms = {expected_kline1_open_time_ms}")
    print(f"TEST CALC: mock_klines_db[1].open_time (from ORM) = {mock_klines_db[1].open_time}")

    # Fetch the data via API (no start/end_ms, should get both sorted)
    response = await test_client.get(f"/data/klines/{symbol}/{timeframe}")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    print(f"Initial response data: {response_data}") # Debug print

    assert len(response_data["klines"]) == 2
    api_kline_resp0 = response_data["klines"][0]
    api_kline_resp1 = response_data["klines"][1]

    assert api_kline_resp0["symbol"] == symbol
    assert api_kline_resp0["timeframe"] == timeframe
    assert api_kline_resp0["open_time"] == expected_kline0_open_time_ms
    assert float(api_kline_resp0["open_price"]) == float(mock_klines_db[0].open_price)
    assert float(api_kline_resp0["close_price"]) == float(mock_klines_db[0].close_price)

    assert api_kline_resp1["open_time"] == expected_kline1_open_time_ms
    assert float(api_kline_resp1["high_price"]) == float(mock_klines_db[1].high_price)

    # Test with limit
    response_limit = await test_client.get(f"/data/klines/{symbol}/{timeframe}?limit=1")
    assert response_limit.status_code == status.HTTP_200_OK
    response_data_limit = response_limit.json()
    assert len(response_data_limit["klines"]) == 1
    assert response_data_limit["klines"][0]["open_time"] == expected_kline0_open_time_ms # Expects the first (oldest)

    # Test with start_ms
    start_ms_val = expected_kline1_open_time_ms
    print(f"Querying with start_ms: {start_ms_val}")
    print(f"Mock Kline 0 open_time_ms: {expected_kline0_open_time_ms}")
    print(f"Mock Kline 1 open_time_ms: {expected_kline1_open_time_ms}")

    response_start_ms = await test_client.get(f"/data/klines/{symbol}/{timeframe}?start_ms={start_ms_val}")
    assert response_start_ms.status_code == status.HTTP_200_OK
    response_data_start_ms = response_start_ms.json()
    print(f"Response for start_ms={start_ms_val}: {response_data_start_ms}")
    assert len(response_data_start_ms["klines"]) == 1
    assert response_data_start_ms["klines"][0]["open_time"] == expected_kline1_open_time_ms

    # Test with start_ms slightly after kline1
    start_ms_val_after = expected_kline1_open_time_ms + 1
    response_start_ms_after = await test_client.get(f"/data/klines/{symbol}/{timeframe}?start_ms={start_ms_val_after}")
    assert response_start_ms_after.status_code == status.HTTP_200_OK
    response_data_start_ms_after = response_start_ms_after.json()
    print(f"Response for start_ms={start_ms_val_after}: {response_data_start_ms_after}")
    assert len(response_data_start_ms_after["klines"]) == 0 

async def test_get_klines_from_redis_cache(test_client: AsyncClient, mocker):
    """Test fetching klines primarily from Redis cache."""
    import json
    from backend.app.config import settings
    from unittest.mock import MagicMock

    symbol = "REDISCOIN/USD"
    timeframe = "1m"
    
    # Mock data to be returned by Redis
    # Timestamps should be in milliseconds for JSON, Pydantic will parse them into datetime
    # for KlineRead's datetime fields.
    current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    # Ensure these times are within API_REDIS_LOOKBACK_MS
    mock_kline_redis_1_ot = current_time_ms - (settings.API_REDIS_LOOKBACK_MS // 2) - 60000 
    mock_kline_redis_2_ot = current_time_ms - (settings.API_REDIS_LOOKBACK_MS // 2)

    mock_redis_data = [
        json.dumps({
            "symbol": symbol, "timeframe": timeframe, "open_time": mock_kline_redis_1_ot,
            "open_price": 200.0, "high_price": 205.0, "low_price": 199.0, "close_price": 202.0,
            "volume": 2000.0, "close_time": mock_kline_redis_1_ot + 59999,
            "quote_asset_volume": 200000.0, "number_of_trades": 200,
            "taker_buy_base_asset_volume": 1000.0, "taker_buy_quote_asset_volume": 100000.0,
            "is_closed": True
        }),
        json.dumps({
            "symbol": symbol, "timeframe": timeframe, "open_time": mock_kline_redis_2_ot,
            "open_price": 202.0, "high_price": 208.0, "low_price": 201.0, "close_price": 207.0,
            "volume": 2500.0, "close_time": mock_kline_redis_2_ot + 59999,
            "quote_asset_volume": 253500.0, "number_of_trades": 250,
            "taker_buy_base_asset_volume": 1200.0, "taker_buy_quote_asset_volume": 122400.0,
            "is_closed": True
        })
    ]

    # Mock Redis client and its methods
    mock_redis_client = MagicMock()
    # zrangebyscore is called with (name, min, max)
    # The API calculates effective_redis_query_start_ms and actual_end_ms
    mock_redis_client.zrangebyscore.return_value = mock_redis_data
    mock_redis_client.get.return_value = None # No backfill status for this test

    # Patch get_redis_connection to return our mock client
    mocker.patch("backend.app.redis_utils.get_redis_connection", return_value=mock_redis_client)
    # Also need to patch it for the data router where it's imported directly for status check
    mocker.patch("backend.app.routers.data.get_redis_connection", return_value=mock_redis_client)


    # API call - no start/end, should rely on API_REDIS_LOOKBACK_MS
    # and MAX_KLINES_IN_REDIS for its internal Redis query range.
    # The DB should not be hit if Redis provides enough data within the lookback window.
    response = await test_client.get(f"/data/klines/{symbol}/{timeframe}?limit=2")
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    # Assertions
    mock_redis_client.zrangebyscore.assert_called_once()
    # We don't mock the DB, so if it were called, it would be an actual DB call
    # or fail if override_get_db is not used. For this test, we assume DB is not called.
    # A more robust check would be to mock db.execute and assert it's not called.

    assert len(response_data["klines"]) == 2
    assert response_data["klines"][0]["open_time"] == mock_kline_redis_1_ot
    assert response_data["klines"][1]["open_time"] == mock_kline_redis_2_ot
    assert float(response_data["klines"][0]["open_price"]) == 200.0
    assert float(response_data["klines"][1]["close_price"]) == 207.0
    assert response_data["backfill_status"] is None

    # Test with a start_ms that should still be covered by Redis
    # And this start_ms is more recent than mock_kline_redis_1_ot
    start_ms_for_filter = mock_kline_redis_1_ot + 1 
    
    # Reset call count for zrangebyscore for the next call
    mock_redis_client.zrangebyscore.reset_mock()

    response_filtered = await test_client.get(f"/data/klines/{symbol}/{timeframe}?limit=2&start_ms={start_ms_for_filter}")
    assert response_filtered.status_code == status.HTTP_200_OK
    response_data_filtered = response_filtered.json()
    
    # zrangebyscore should be called again
    mock_redis_client.zrangebyscore.assert_called_once()
    
    # The API's internal logic fetches a range from Redis, then filters by start_ms.
    # So, if start_ms_for_filter > mock_kline_redis_1_ot, only the second kline should remain.
    assert len(response_data_filtered["klines"]) == 1
    assert response_data_filtered["klines"][0]["open_time"] == mock_kline_redis_2_ot 

async def test_get_klines_from_redis_and_db(test_client: AsyncClient, db_session, override_get_db, mocker):
    """Test fetching klines from both Redis cache and the database."""
    import json
    from backend.app.models import Kline
    from backend.app.config import settings
    from decimal import Decimal
    from unittest.mock import MagicMock

    symbol = "MIXCOIN/USD"
    timeframe = "5m"
    limit = 4 # We'll have 2 in Redis, 2 in DB

    current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Mock data for Redis (more recent)
    # Ensure these times are within API_REDIS_LOOKBACK_MS
    redis_kline_1_ot = current_time_ms - (settings.API_REDIS_LOOKBACK_MS // 3) - 5*60000 # 5m before next
    redis_kline_2_ot = current_time_ms - (settings.API_REDIS_LOOKBACK_MS // 3)

    mock_redis_data = [
        json.dumps({
            "symbol": symbol, "timeframe": timeframe, "open_time": redis_kline_1_ot,
            "open_price": 300.0, "high_price": 305.0, "low_price": 299.0, "close_price": 302.0,
            "volume": 3000.0, "close_time": redis_kline_1_ot + 5*60000 -1,
            "quote_asset_volume": 300000.0, "number_of_trades": 300,
            "taker_buy_base_asset_volume": 1500.0, "taker_buy_quote_asset_volume": 150000.0,
            "is_closed": True
        }),
        json.dumps({
            "symbol": symbol, "timeframe": timeframe, "open_time": redis_kline_2_ot,
            "open_price": 302.0, "high_price": 308.0, "low_price": 301.0, "close_price": 307.0,
            "volume": 3500.0, "close_time": redis_kline_2_ot + 5*60000 -1,
            "quote_asset_volume": 353500.0, "number_of_trades": 350,
            "taker_buy_base_asset_volume": 1700.0, "taker_buy_quote_asset_volume": 172400.0,
            "is_closed": True
        })
    ]

    # Mock data for DB (older than Redis data)
    # open_time should be datetime for DB model
    db_kline_1_dt = datetime.fromtimestamp((redis_kline_1_ot - 2*5*60000) / 1000.0, tz=timezone.utc) # 2 intervals before 1st redis kline
    db_kline_2_dt = datetime.fromtimestamp((redis_kline_1_ot - 1*5*60000) / 1000.0, tz=timezone.utc) # 1 interval before 1st redis kline

    mock_klines_db = [
        Kline(
            symbol=symbol, timeframe=timeframe, open_time=db_kline_1_dt,
            open_price=Decimal("290.0"), high_price=Decimal("295.0"), low_price=Decimal("289.0"), close_price=Decimal("292.0"),
            volume=Decimal("4000.0"), close_time=db_kline_1_dt + timedelta(minutes=4, seconds=59, milliseconds=999),
            quote_asset_volume=Decimal("400000.0"), number_of_trades=400,
            taker_buy_base_asset_volume=Decimal("2000.0"), taker_buy_quote_asset_volume=Decimal("200000.0")
        ),
        Kline(
            symbol=symbol, timeframe=timeframe, open_time=db_kline_2_dt,
            open_price=Decimal("292.0"), high_price=Decimal("298.0"), low_price=Decimal("291.0"), close_price=Decimal("297.0"),
            volume=Decimal("4500.0"), close_time=db_kline_2_dt + timedelta(minutes=4, seconds=59, milliseconds=999),
            quote_asset_volume=Decimal("453500.0"), number_of_trades=450,
            taker_buy_base_asset_volume=Decimal("2200.0"), taker_buy_quote_asset_volume=Decimal("222400.0")
        ),
    ]
    db_session.add_all(mock_klines_db)
    db_session.commit()

    # Expected timestamps in ms for DB klines
    expected_db_kline_1_ot_ms = int(db_kline_1_dt.timestamp() * 1000)
    expected_db_kline_2_ot_ms = int(db_kline_2_dt.timestamp() * 1000)

    # Mock Redis client
    mock_redis_client = MagicMock()
    mock_redis_client.zrangebyscore.return_value = mock_redis_data
    mock_redis_client.get.return_value = None # No backfill status

    mocker.patch("backend.app.redis_utils.get_redis_connection", return_value=mock_redis_client)
    mocker.patch("backend.app.routers.data.get_redis_connection", return_value=mock_redis_client)

    # API Call - should fetch from both Redis and DB
    response = await test_client.get(f"/data/klines/{symbol}/{timeframe}?limit={limit}")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    mock_redis_client.zrangebyscore.assert_called_once()
    # DB should also be queried. We can check the arguments if we mock execute, but for now, rely on combined data.
    
    assert len(response_data["klines"]) == limit # Expecting 2 from DB + 2 from Redis
    
    # Check sorting and content - DB klines first (older), then Redis klines (newer)
    assert response_data["klines"][0]["open_time"] == expected_db_kline_1_ot_ms
    assert float(response_data["klines"][0]["open_price"]) == 290.0
    assert response_data["klines"][1]["open_time"] == expected_db_kline_2_ot_ms
    assert float(response_data["klines"][1]["close_price"]) == 297.0

    assert response_data["klines"][2]["open_time"] == redis_kline_1_ot
    assert float(response_data["klines"][2]["open_price"]) == 300.0
    assert response_data["klines"][3]["open_time"] == redis_kline_2_ot
    assert float(response_data["klines"][3]["close_price"]) == 307.0

    # Verify that the DB query was likely made with end_ms adjusted by Redis data
    # The oldest Redis kline is redis_kline_1_ot. DB query end_ms should be redis_kline_1_ot - 1.
    # This requires inspecting the DB query. For now, the combined data correctness is a good indicator.
    # To explicitly check the DB query parameters, we would need to mock `db.execute`. 

async def test_get_klines_backfill_status_reporting(test_client: AsyncClient, mocker):
    """Test reporting of backfill status from Redis."""
    import json
    from unittest.mock import MagicMock
    import time

    symbol = "BACKFILLCOIN/USD"
    timeframe = "1h"

    mock_redis_client = MagicMock()
    mock_redis_client.zrangebyscore.return_value = [] # No kline data from Redis for this test
    
    # Patch get_redis_connection
    # Note: We patch both locations where get_redis_connection might be called from within data.py
    mocker.patch("backend.app.redis_utils.get_redis_connection", return_value=mock_redis_client)
    mocker.patch("backend.app.routers.data.get_redis_connection", return_value=mock_redis_client)

    # Scenario 1: Backfill in progress
    current_ts_seconds = int(time.time())
    backfill_status_in_progress = {"status": "in_progress", "last_updated_ts": current_ts_seconds}
    mock_redis_client.get.return_value = json.dumps(backfill_status_in_progress)
    
    response_in_progress = await test_client.get(f"/data/klines/{symbol}/{timeframe}")
    assert response_in_progress.status_code == status.HTTP_200_OK
    data_in_progress = response_in_progress.json()
    assert data_in_progress["klines"] == []
    assert data_in_progress["backfill_status"] == "in_progress"
    assert data_in_progress["backfill_last_updated_ts"] == current_ts_seconds
    mock_redis_client.get.assert_called_once_with(f"backfill_status:{symbol.upper()}:{timeframe}")

    # Scenario 2: Stale backfill status
    mock_redis_client.get.reset_mock()
    stale_ts_seconds = current_ts_seconds - (2 * 60 * 60) # 2 hours ago
    backfill_status_stale = {"status": "in_progress", "last_updated_ts": stale_ts_seconds}
    mock_redis_client.get.return_value = json.dumps(backfill_status_stale)

    response_stale = await test_client.get(f"/data/klines/{symbol}/{timeframe}")
    assert response_stale.status_code == status.HTTP_200_OK
    data_stale = response_stale.json()
    assert data_stale["klines"] == []
    assert data_stale["backfill_status"] == "stale_in_progress"
    assert data_stale["backfill_last_updated_ts"] == stale_ts_seconds
    mock_redis_client.get.assert_called_once_with(f"backfill_status:{symbol.upper()}:{timeframe}")

    # Scenario 3: No backfill status
    mock_redis_client.get.reset_mock()
    mock_redis_client.get.return_value = None

    response_none = await test_client.get(f"/data/klines/{symbol}/{timeframe}")
    assert response_none.status_code == status.HTTP_200_OK
    data_none = response_none.json()
    assert data_none["klines"] == []
    assert data_none["backfill_status"] is None
    assert data_none["backfill_last_updated_ts"] is None
    mock_redis_client.get.assert_called_once_with(f"backfill_status:{symbol.upper()}:{timeframe}")

    # Scenario 4: Malformed backfill status in Redis (should be handled gracefully)
    mock_redis_client.get.reset_mock()
    mock_redis_client.get.return_value = "not_json_parsable_string"

    response_malformed = await test_client.get(f"/data/klines/{symbol}/{timeframe}")
    assert response_malformed.status_code == status.HTTP_200_OK
    data_malformed = response_malformed.json()
    assert data_malformed["klines"] == []
    assert data_malformed["backfill_status"] is None # Expect graceful handling
    assert data_malformed["backfill_last_updated_ts"] is None
    mock_redis_client.get.assert_called_once_with(f"backfill_status:{symbol.upper()}:{timeframe}") 