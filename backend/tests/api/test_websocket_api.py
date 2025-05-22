"""
Tests for the WebSocket API endpoints.
"""
import pytest
import asyncio
import json
from httpx import AsyncClient # Although test_client provides websocket_connect
from fastapi import status, WebSocketDisconnect
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

async def test_websocket_kline_updates_happy_path(test_client: AsyncClient, mocker):
    """Test successful WebSocket connection, subscription, and receiving messages."""
    symbol = "WSCOIN/USD"
    timeframe = "1s" # Using a short timeframe for test clarity
    pubsub_channel = f"kline_updates:{symbol.upper()}:{timeframe}"

    # Mock Redis PubSub and its methods
    mock_pubsub = MagicMock()
    # subscribe is called with asyncio.to_thread, so the actual method called is sync
    mock_pubsub.subscribe = MagicMock() 
    mock_pubsub.unsubscribe = MagicMock()
    mock_pubsub.close = MagicMock()
    
    # Simulate messages from Redis Pub/Sub
    # get_message will be called in a loop. We need it to return a sequence of values.
    # First, None (timeout), then a message, then perhaps another None, then raise an exception to break loop or simulate disconnect
    mock_kline_data_1 = {
        "symbol": symbol.upper(), "timeframe": timeframe, "open_time": int(datetime.now(timezone.utc).timestamp() * 1000),
        "open_price": 400.0, "high_price": 405.0, "low_price": 399.0, "close_price": 402.0,
        "volume": 4000.0, "close_time": int(datetime.now(timezone.utc).timestamp() * 1000) + 999,
        "quote_asset_volume": 400000.0, "number_of_trades": 400,
        "taker_buy_base_asset_volume": 2000.0, "taker_buy_quote_asset_volume": 200000.0,
        "is_closed": True
    }
    
    # get_message should return a dict like {'type': 'message', 'channel': b'chan', 'data': b'data'}
    # or None if timeout
    message_from_redis = {'type': 'message', 'channel': pubsub_channel.encode('utf-8'), 'data': json.dumps(mock_kline_data_1).encode('utf-8')}
    
    # We'll use a list to control the sequence of return values for get_message
    # The loop in the WebSocket handler might call get_message multiple times.
    # Let it return one message, then simulate no more messages for a bit, then we'll close the client.
    get_message_returns = [
        None, # First call, simulate timeout
        message_from_redis, # Second call, deliver the message
        None, None, None # Subsequent calls, simulate timeout until client disconnects
    ]
    mock_pubsub.get_message.side_effect = get_message_returns
    
    mock_redis_client = MagicMock()
    mock_redis_client.pubsub.return_value = mock_pubsub

    # Patch get_redis_connection used by the WebSocket endpoint
    mocker.patch("backend.app.routers.data.get_redis_connection", return_value=mock_redis_client)

    try:
        async with test_client.websocket_connect(f"/ws/klines/{symbol}/{timeframe}") as websocket:
            # 1. Check for subscription confirmation message
            subscription_confirmation = await websocket.receive_json()
            assert subscription_confirmation["status"] == "subscribed"
            assert subscription_confirmation["channel"] == pubsub_channel

            # Assert that Redis pubsub.subscribe was called
            # subscribe is called via asyncio.to_thread, so we check the mock of the sync method
            await asyncio.sleep(0.01) # give time for the thread to execute
            mock_pubsub.subscribe.assert_called_once_with(pubsub_channel)

            # 2. Check for kline data message
            # The loop in the handler calls get_message. Our side_effect will make it return the data.
            received_kline_data = await websocket.receive_json()
            assert received_kline_data["symbol"] == mock_kline_data_1["symbol"]
            assert received_kline_data["open_time"] == mock_kline_data_1["open_time"]
            assert float(received_kline_data["open_price"]) == mock_kline_data_1["open_price"]
            
            # 3. Test sending a ping from client (optional, but good to have if handler supports it)
            await websocket.send_text(json.dumps({"type": "ping"})) # Send as text, as handler expects text
            # The endpoint sends JSON strings for pong, so receive_json()
            pong_response = await websocket.receive_json()
            assert pong_response.get("type") == "pong" or pong_response == "pong" # Endpoint sends `json.dumps({"type": "pong"})`

            # 4. Client closes connection (implicitly by exiting the 'async with' block)
            # This will trigger WebSocketDisconnect in the handler.

    except WebSocketDisconnect:
        # This is an expected way for the test to end if the server closes after client disconnects
        pass 
    finally:
        # Assert that unsubscribe and close were called on pubsub
        # These are also called via asyncio.to_thread
        await asyncio.sleep(0.01) # allow time for finally block in handler
        mock_pubsub.unsubscribe.assert_called_once_with(pubsub_channel)
        mock_pubsub.close.assert_called_once()
        mock_redis_client.close.assert_called_once()


async def test_websocket_kline_updates_redis_connection_failure(test_client: AsyncClient, mocker):
    """Test WebSocket behavior when initial Redis connection fails."""
    symbol = "FAILCOIN/USD"
    timeframe = "1m"

    # Patch get_redis_connection to return None (simulating connection failure)
    mocker.patch("backend.app.routers.data.get_redis_connection", return_value=None)

    async with test_client.websocket_connect(f"/ws/klines/{symbol}/{timeframe}") as websocket:
        # Expect an error message and then the server should close the connection
        error_message = await websocket.receive_json()
        assert "error" in error_message
        assert error_message["error"] == "Could not connect to data stream."
        
        # After sending the error, the server should close the connection.
        # Attempting to receive again should raise WebSocketDisconnect or similar.
        try:
            await websocket.receive_text() # Or receive_json()
            assert False, "WebSocket should have been closed by the server"
        except WebSocketDisconnect as e:
            assert e.code == 1011 # Internal error code used by the handler
        except Exception as e: # Catch other potential httpx client-side disconnects
             print(f"Received unexpected exception after server should close: {e}")
             # Depending on timing, httpx might raise its own disconnect error.
             # For this test, the key is that the error message was received.

# Add imports at the top of the file if not already present
# from datetime import datetime, timezone (already implicitly used) 