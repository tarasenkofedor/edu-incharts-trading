"""
Tests for the Historical Data Fetcher for Binance API.
"""
import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from backend.data_ingestion_service.historical_data_fetcher import (
    fetch_historical_klines,
    save_historical_klines_to_db # Will need to mock DB interactions for this
)
from backend.app.models import Kline
from backend.app.config import Settings # For API keys if used directly, or defaults
from backend.app.database import SessionLocal # For save_historical_klines_to_db tests

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_settings_with_api_keys():
    return Settings(BINANCE_API_KEY="test_api_key", BINANCE_SECRET_KEY="test_secret_key")

@pytest.fixture
def mock_settings_no_api_keys():
    return Settings(BINANCE_API_KEY=None, BINANCE_SECRET_KEY=None)

# --- Tests for fetch_historical_klines --- 

async def test_fetch_historical_klines_success_single_page(mock_settings_no_api_keys):
    """Test successful fetching of klines that fit in a single API response."""
    symbol = "BTCUSDT"
    timeframe = "1m"
    start_time_ms = 1678886400000 # 2023-03-15 12:00:00 UTC
    end_time_ms = start_time_ms + 2 * 60000 -1 # 2 klines worth
    limit_per_call = 500 # Binance default

    # Mock Binance API response for klines
    mock_api_response_data = [
        [start_time_ms, "20000.0", "20600.0", "19900.0", "20500.0", "1000.0", start_time_ms + 59999, "20250000.0", 100, "500.0", "10125000.0", "0"],
        [start_time_ms + 60000, "20500.0", "20700.0", "20300.0", "20600.0", "1200.0", start_time_ms + 60000 + 59999, "24660000.0", 120, "600.0", "12330000.0", "0"]
    ]

    mock_response = httpx.Response(200, json=mock_api_response_data)
    mock_async_client = AsyncMock(spec=httpx.AsyncClient)
    mock_async_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_async_client) as mock_client_constructor:
        with patch("backend.data_ingestion_service.historical_data_fetcher.settings", mock_settings_no_api_keys):
            fetched_klines = await fetch_historical_klines(symbol, timeframe, start_time_ms, end_time_ms)

            mock_client_constructor.assert_called_once() # Check AsyncClient was instantiated
            mock_async_client.get.assert_called_once()
            args, kwargs = mock_async_client.get.call_args
            assert args[0] == "https://api.binance.com/api/v3/klines"
            assert kwargs["params"]["symbol"] == symbol
            assert kwargs["params"]["interval"] == timeframe
            assert kwargs["params"]["startTime"] == start_time_ms
            assert kwargs["params"]["endTime"] == end_time_ms
            assert kwargs["params"]["limit"] == limit_per_call
            assert "X-MBX-APIKEY" not in kwargs.get("headers", {})

            assert len(fetched_klines) == 2
            assert isinstance(fetched_klines[0], Kline)
            assert fetched_klines[0].symbol == symbol
            assert fetched_klines[0].timeframe == timeframe
            assert fetched_klines[0].open_time == start_time_ms
            assert fetched_klines[0].open_price == Decimal("20000.0")
            assert fetched_klines[1].close_price == Decimal("20600.0")

async def test_fetch_historical_klines_with_api_keys(mock_settings_with_api_keys):
    """Test that API key is included in headers when configured."""
    mock_api_response_data = []
    mock_response = httpx.Response(200, json=mock_api_response_data)
    mock_async_client = AsyncMock(spec=httpx.AsyncClient)
    mock_async_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        with patch("backend.data_ingestion_service.historical_data_fetcher.settings", mock_settings_with_api_keys):
            await fetch_historical_klines("BTCUSDT", "1h", 1678886400000)
            args, kwargs = mock_async_client.get.call_args
            assert "X-MBX-APIKEY" in kwargs.get("headers", {})
            assert kwargs["headers"]["X-MBX-APIKEY"] == "test_api_key"

async def test_fetch_historical_klines_pagination(mock_settings_no_api_keys):
    """Test fetching klines that require multiple API calls (pagination)."""
    symbol = "ETHUSDT"
    timeframe = "1d"
    # Simulate 3 klines, Binance default limit is 500, but we'll mock it lower for test simplicity if needed
    # For this test, let's assume limit_per_call is effectively 2 for mocking.
    # Fetcher uses a fixed internal limit_per_call (e.g. 1000), so API will just return fewer if that's all.
    # We test pagination by making the API return data indicating more could be fetched.
    
    start_time_ms = 1678886400000 # Day 1
    kline1_data = [start_time_ms, "1500", "1550", "1480", "1520", "5000", start_time_ms + 24*60*60000-1, "..."]
    kline2_start_ms = start_time_ms + 24*60*60000 # Day 2
    kline2_data = [kline2_start_ms, "1520", "1600", "1500", "1580", "6000", kline2_start_ms + 24*60*60000-1, "..."]
    kline3_start_ms = kline2_start_ms + 24*60*60000 # Day 3
    kline3_data = [kline3_start_ms, "1580", "1650", "1570", "1630", "5500", kline3_start_ms + 24*60*60000-1, "..."]

    # Mock responses: first call returns 2 klines, second call returns 1 kline
    mock_response1 = httpx.Response(200, json=[kline1_data, kline2_data])
    mock_response2 = httpx.Response(200, json=[kline3_data])
    # A subsequent call (if made) would return empty, signaling end of data
    mock_response_empty = httpx.Response(200, json=[]) 

    mock_async_client = AsyncMock(spec=httpx.AsyncClient)
    mock_async_client.get.side_effect = [mock_response1, mock_response2, mock_response_empty]

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        with patch("backend.data_ingestion_service.historical_data_fetcher.settings", mock_settings_no_api_keys):
            # Fetch up to day 3 (exclusive end for kline3 means it should be included)
            # The loop continues as long as the number of returned klines matches limit_per_call (1000 by default)
            # or until end_time_ms is reached if specified.
            # For this test, we rely on empty response to stop.
            fetched_klines = await fetch_historical_klines(symbol, timeframe, start_time_ms, end_time_ms=kline3_start_ms + 1000)

            assert mock_async_client.get.call_count == 3 # Call 1 (2 klines), Call 2 (1 kline), Call 3 (0 klines to confirm end)
            
            # Check params of first call
            args1, kwargs1 = mock_async_client.get.call_args_list[0]
            assert kwargs1["params"]["startTime"] == start_time_ms
            
            # Check params of second call (startTime should be kline3_start_ms, as kline2 was last of previous batch)
            args2, kwargs2 = mock_async_client.get.call_args_list[1]
            assert kwargs2["params"]["startTime"] == kline3_start_ms 
            
            # Check params of third call (startTime should be after kline3)
            args3, kwargs3 = mock_async_client.get.call_args_list[2]
            assert kwargs3["params"]["startTime"] > kline3_start_ms

            assert len(fetched_klines) == 3
            assert fetched_klines[0].open_time == start_time_ms
            assert fetched_klines[1].open_time == kline2_start_ms
            assert fetched_klines[2].open_time == kline3_start_ms

async def test_fetch_historical_klines_rate_limit_retry(mock_settings_no_api_keys):
    """Test retry logic on encountering 429/418 rate limit errors."""
    symbol = "LTCUSDT"
    timeframe = "4h"
    start_time_ms = 1678886400000

    mock_api_kline_data = [[start_time_ms, "100", "105", "99", "102", "2000", start_time_ms+4*60*60000-1, "..."]]
    
    # Simulate 429, then 418, then success
    response_429 = httpx.Response(429, json={"msg": "Rate limit exceeded"})
    response_418 = httpx.Response(418, json={"msg": "IP banned"}) # Binance uses 418 for IP bans
    response_success = httpx.Response(200, json=mock_api_kline_data)

    mock_async_client = AsyncMock(spec=httpx.AsyncClient)
    # Configure side_effect for multiple calls to client.get()
    mock_async_client.get.side_effect = [response_429, response_418, response_success, httpx.Response(200, json=[])] # Last empty to stop pagination
    
    # Patch asyncio.sleep to avoid actual delays in test
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch("httpx.AsyncClient", return_value=mock_async_client):
            with patch("backend.data_ingestion_service.historical_data_fetcher.settings", mock_settings_no_api_keys):
                # Retry parameters are hardcoded in fetcher for now, but this tests if it retries.
                fetched_klines = await fetch_historical_klines(symbol, timeframe, start_time_ms, start_time_ms + 1000)

                assert mock_async_client.get.call_count == 4 # 429, 418, success, empty_page
                assert mock_sleep.call_count == 2 # Should sleep after 429 and 418
                assert len(fetched_klines) == 1
                assert fetched_klines[0].open_price == Decimal("100")

async def test_fetch_historical_klines_http_request_error(mock_settings_no_api_keys):
    """Test retry logic on httpx.RequestError."""
    symbol = "XRPUSDT"
    timeframe = "1h"
    start_time_ms = 1678886400000
    mock_api_kline_data = [[start_time_ms, "0.5", "0.52", "0.48", "0.51", "1000000", start_time_ms+60*60000-1, "..."]]

    # Simulate RequestError, then success
    response_success = httpx.Response(200, json=mock_api_kline_data)
    mock_async_client = AsyncMock(spec=httpx.AsyncClient)
    mock_async_client.get.side_effect = [httpx.RequestError("Network error"), response_success, httpx.Response(200, json=[])]

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch("httpx.AsyncClient", return_value=mock_async_client):
            with patch("backend.data_ingestion_service.historical_data_fetcher.settings", mock_settings_no_api_keys):
                fetched_klines = await fetch_historical_klines(symbol, timeframe, start_time_ms, start_time_ms + 1000)

                assert mock_async_client.get.call_count == 3 # RequestError, success, empty_page
                assert mock_sleep.call_count == 1 # Sleep after RequestError
                assert len(fetched_klines) == 1
                assert fetched_klines[0].open_price == Decimal("0.5")

async def test_fetch_historical_klines_other_http_error_no_retry(mock_settings_no_api_keys):
    """Test that other HTTP errors (e.g., 400 Bad Request) do not cause retries and raise an exception."""
    symbol = "ADAUSDT"
    timeframe = "15m"
    start_time_ms = 1678886400000

    response_400 = httpx.Response(400, json={"code": -1102, "msg": "Mandatory parameter 'symbol' was not sent, or the empty string was used."})
    mock_async_client = AsyncMock(spec=httpx.AsyncClient)
    mock_async_client.get.return_value = response_400

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch("httpx.AsyncClient", return_value=mock_async_client):
            with patch("backend.data_ingestion_service.historical_data_fetcher.settings", mock_settings_no_api_keys):
                with pytest.raises(httpx.HTTPStatusError) as excinfo:
                    await fetch_historical_klines(symbol, timeframe, start_time_ms)
                
                assert excinfo.value.response.status_code == 400
                mock_async_client.get.assert_called_once() # Should not retry
                mock_sleep.assert_not_called() # No sleep for non-retryable errors

# --- Tests for save_historical_klines_to_db --- 
# These will require mocking the database session and execute methods.
# For now, this is a placeholder. A more complete test would use a test DB setup or deeper mocking.

@pytest.fixture
def mock_db_session_factory():
    mock_session = MagicMock(spec=SessionLocal)
    mock_session.execute = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.close = MagicMock()
    
    # Simulate result of execute for insert (e.g. rowcount)
    # For `insert(...).on_conflict_do_nothing()`, rowcount is not directly useful for inserted vs conflicted.
    # The function save_historical_klines_to_db returns (inserted_count, conflict_count) but 
    # this requires a more complex mock of the result proxy or a real DB with data.
    # For a simple mock, let's assume it always succeeds and affects N rows.
    # A proper mock would require a `ResultProxy` that can be iterated or has `returned_defaults()` etc.
    # For now, we just check if execute is called.
    mock_execute_result = MagicMock()
    # mock_execute_result.returned_defaults = lambda: iter([]) # if returning=* used
    mock_session.execute.return_value = mock_execute_result

    return MagicMock(return_value=mock_session) # Factory returns the mock_session

async def test_save_historical_klines_to_db_empty_list(mock_db_session_factory):
    """Test saving an empty list of klines."""
    inserted, conflicted = await save_historical_klines_to_db([], mock_db_session_factory)
    assert inserted == 0
    assert conflicted == 0
    mock_db_session_factory().execute.assert_not_called()

async def test_save_historical_klines_to_db_success(mock_db_session_factory):
    """Test saving a list of klines successfully (mocked DB)."""
    klines_to_save = [
        Kline(symbol="BTCUSDT", timeframe="1m", open_time=1678886400000, open_price=Decimal("20000"), high_price=Decimal("20100"), low_price=Decimal("19900"), close_price=Decimal("20050"), volume=Decimal("10"), close_time=1678886459999, quote_asset_volume=Decimal("200000"), number_of_trades=100, taker_buy_base_asset_volume=Decimal("5"), taker_buy_quote_asset_volume=Decimal("100000")),
        Kline(symbol="BTCUSDT", timeframe="1m", open_time=1678886460000, open_price=Decimal("20050"), high_price=Decimal("20150"), low_price=Decimal("20000"), close_price=Decimal("20100"), volume=Decimal("12"), close_time=1678886519999, quote_asset_volume=Decimal("240600"), number_of_trades=120, taker_buy_base_asset_volume=Decimal("6"), taker_buy_quote_asset_volume=Decimal("120300"))
    ]
    
    # To properly test inserted vs conflicted counts, we need a real DB or a much more sophisticated mock
    # of SQLAlchemy execute and result proxy. For now, we focus on whether the insert statement is attempted.
    # The function `save_historical_klines_to_db` currently returns (len(klines), 0) on mocked success path.
    
    # To test the actual SQL, one might capture the statement passed to execute.
    # For now, just verify the call and assume the SQL is correct as it's generated by SQLAlchemy.
    inserted, conflicted = await save_historical_klines_to_db(klines_to_save, mock_db_session_factory)
    
    mock_db_session_factory().execute.assert_called_once()
    mock_db_session_factory().commit.assert_called_once()
    mock_db_session_factory().rollback.assert_not_called()
    mock_db_session_factory().close.assert_called_once()
    
    # Given the current mock, these will be the returned values
    assert inserted == len(klines_to_save)
    assert conflicted == 0

async def test_save_historical_klines_to_db_exception(mock_db_session_factory):
    """Test database exception handling during save."""
    klines_to_save = [Kline(symbol="ETHUSDT", timeframe="5m", open_time=1678880000000, open_price=Decimal("1500"), high_price=Decimal("1510"), low_price=Decimal("1490"), close_price=Decimal("1505"), volume=Decimal("100"), close_time=1678880299999, quote_asset_volume=Decimal("150000"), number_of_trades=50, taker_buy_base_asset_volume=Decimal("50"), taker_buy_quote_asset_volume=Decimal("75000"))]
    
    mock_db_session_factory().execute.side_effect = Exception("DB Save Error")
    
    inserted, conflicted = await save_historical_klines_to_db(klines_to_save, mock_db_session_factory)
    
    mock_db_session_factory().execute.assert_called_once()
    mock_db_session_factory().commit.assert_not_called()
    mock_db_session_factory().rollback.assert_called_once()
    mock_db_session_factory().close.assert_called_once()
    assert inserted == 0
    assert conflicted == 0 