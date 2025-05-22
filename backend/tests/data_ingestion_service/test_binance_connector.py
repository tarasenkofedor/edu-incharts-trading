"""
Tests for the Binance WebSocket Connector.
"""
import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

from backend.data_ingestion_service.binance_connector import BinanceWebSocketManager
from backend.app.config import Settings # To access default retry params if needed

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_settings():
    """Fixture to provide a Settings object for BinanceWebSocketManager."""
    # Provide minimal settings needed for the connector if any
    # For example, if retry parameters were configurable via Settings:
    # return Settings(WS_RECONNECT_MAX_ATTEMPTS=3, WS_RECONNECT_BASE_DELAY=1)
    return Settings() # Default settings are fine for now as params are hardcoded

@pytest.fixture
def mock_data_handler():
    """Fixture for a mock data handler callback."""
    return AsyncMock() # AsyncMock for an async callback

async def test_bwm_successful_connection_and_message_processing(
    mock_settings, mock_data_handler
):
    """Test successful connection, receiving, and processing of a valid kline message."""
    symbol = "BTCUSDT"
    timeframe = "1m"
    shutdown_event = asyncio.Event()

    manager = BinanceWebSocketManager(
        symbol, timeframe, mock_data_handler, shutdown_event,
        max_retries=2, base_delay=0.01 # Fast retries for test
    )

    # Mock the websockets.connect context manager
    mock_websocket_connection = AsyncMock()
    mock_websocket_connection.recv = AsyncMock()
    mock_websocket_connection.send = AsyncMock() # For ping or other sends if any
    mock_websocket_connection.close = AsyncMock()

    # Simulate a valid kline message from Binance
    kline_payload = {
        "e": "kline", "E": 123456789, "s": "BTCUSDT",
        "k": {
            "t": 1678886400000, "T": 1678886459999, "s": "BTCUSDT", "i": "1m",
            "f": 100, "L": 200, "o": "20000.0", "c": "20500.0", "h": "20600.0", "l": "19900.0",
            "v": "1000.0", "n": 100, "x": True, # x=True means kline is closed
            "q": "20250000.0", "V": "500.0", "Q": "10125000.0", "B": "0"
        }
    }
    # The recv() method should return this message, then simulate a disconnect to end the run loop
    mock_websocket_connection.recv.side_effect = [
        json.dumps(kline_payload),
        asyncio.exceptions.CancelledError # Simulate shutdown or clean disconnect to stop run()
    ]

    # Patch websockets.connect to return our mock connection
    with patch("websockets.connect", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_websocket_connection))) as mock_connect_ws:
        # Run the manager in a task so we can control its execution time for the test
        run_task = asyncio.create_task(manager.run())
        
        # Allow the task to run and process the message
        await asyncio.sleep(0.1) # Ensure connect and recv are called

        # Assertions
        mock_connect_ws.assert_called_once_with(f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{timeframe}")
        mock_websocket_connection.recv.assert_called()
        
        # Check that the data_handler was called with the processed kline data
        mock_data_handler.assert_called_once()
        call_args = mock_data_handler.call_args[0][0] # Get the first positional arg of the call
        
        assert call_args["symbol"] == "BTCUSDT"
        assert call_args["timeframe"] == "1m"
        assert call_args["open_time"] == 1678886400000
        assert call_args["open_price"] == "20000.0" # Stays as string from Binance
        assert call_args["is_closed"] is True

        # Trigger shutdown and wait for the task to complete
        shutdown_event.set()
        await run_task # ensure task finishes cleanly

async def test_bwm_reconnection_logic(mock_settings, mock_data_handler):
    """Test the reconnection logic of BinanceWebSocketManager."""
    symbol = "ETHUSDT"
    timeframe = "5m"
    shutdown_event = asyncio.Event()

    manager = BinanceWebSocketManager(
        symbol, timeframe, mock_data_handler, shutdown_event,
        max_retries=3, base_delay=0.01 # Allow a few fast retries
    )

    mock_websocket_connection = AsyncMock()
    mock_websocket_connection.recv = AsyncMock(side_effect=asyncio.exceptions.CancelledError) # Immediate disconnect on successful connect
    mock_websocket_connection.send = AsyncMock()
    mock_websocket_connection.close = AsyncMock()

    # Simulate connection failure for the first two attempts, then success on the third
    mock_connect_context_manager = AsyncMock(__aenter__=AsyncMock(return_value=mock_websocket_connection))
    
    with patch("websockets.connect") as mock_connect_ws:
        mock_connect_ws.side_effect = [
            ConnectionRefusedError("Connection failed attempt 1"), # First attempt fails
            ConnectionRefusedError("Connection failed attempt 2"), # Second attempt fails
            mock_connect_context_manager # Third attempt succeeds
        ]

        run_task = asyncio.create_task(manager.run())
        await asyncio.sleep(0.1) # Allow time for connection attempts and processing

        assert mock_connect_ws.call_count == 3 # Should attempt to connect 3 times
        # The successful connection should have led to recv being called (which then disconnects)
        mock_websocket_connection.recv.assert_called_once()
        
        # Data handler should not have been called as recv disconnects immediately
        mock_data_handler.assert_not_called()

        shutdown_event.set()
        await run_task

async def test_bwm_max_retries_exceeded(mock_settings, mock_data_handler):
    """Test that the manager stops after exceeding max retries."""
    symbol = "BNBUSDT"
    timeframe = "1h"
    shutdown_event = asyncio.Event()
    max_retries_for_test = 2

    manager = BinanceWebSocketManager(
        symbol, timeframe, mock_data_handler, shutdown_event,
        max_retries=max_retries_for_test, base_delay=0.01
    )

    # Simulate persistent connection failure
    with patch("websockets.connect", side_effect=ConnectionRefusedError("Persistent connection failure")) as mock_connect_ws:
        # No need for create_task here, run() should exit after max_retries
        await manager.run() 

        # Connect should be called max_retries + 1 times (initial attempt + retries)
        assert mock_connect_ws.call_count == max_retries_for_test + 1
        mock_data_handler.assert_not_called()
        # shutdown_event should not be set by the manager in this case, it just stops trying.

async def test_bwm_shutdown_event_stops_manager(mock_settings, mock_data_handler):
    """Test that setting the shutdown_event stops the manager."""
    symbol = "XRPUSDT"
    timeframe = "4h"
    shutdown_event = asyncio.Event()

    manager = BinanceWebSocketManager(
        symbol, timeframe, mock_data_handler, shutdown_event,
        max_retries=5, base_delay=0.01
    )

    # Simulate a connected state where it's just waiting for recv
    mock_websocket_connection = AsyncMock()
    # recv will block indefinitely (or until shutdown_event is set and run_task cancelled)
    mock_websocket_connection.recv = AsyncMock(side_effect=asyncio.Future()) 
    mock_websocket_connection.send = AsyncMock()
    mock_websocket_connection.close = AsyncMock()

    with patch("websockets.connect", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_websocket_connection))) as mock_connect_ws:
        run_task = asyncio.create_task(manager.run())
        
        await asyncio.sleep(0.02) # Allow connect and initial recv call setup
        mock_connect_ws.assert_called_once()
        mock_websocket_connection.recv.assert_called_once() # It should be called and waiting

        shutdown_event.set() # Trigger shutdown
        
        # Wait for the task to complete (should be quick due to shutdown_event)
        try:
            await asyncio.wait_for(run_task, timeout=0.1)
        except asyncio.TimeoutError:
            pytest.fail("Manager did not stop in time after shutdown event")

        # Check if close was called on the WebSocket (graceful shutdown)
        mock_websocket_connection.close.assert_called_once()
        mock_data_handler.assert_not_called() # No data was sent 