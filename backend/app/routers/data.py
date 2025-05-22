from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
import pandas as pd
import io
import time # For current time
import json # For parsing Redis data
import logging # For logging
import asyncio # Moved to top
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, asc
import redis # For redis.exceptions.ConnectionError or similar
from starlette.websockets import WebSocketState # Added for checking WebSocket state
from datetime import datetime, timezone
import websockets # Make sure this import is present or add it

from ..database import get_db # Assuming get_db yields a session
from ..models import Kline
from ..schemas import KlineRead, KlineHistoricalResponse # Import new response model
from ..redis_utils import get_redis_connection # For Redis connection
from ..config import settings # For API_REDIS_LOOKBACK_MS

logger = logging.getLogger(__name__)
router = APIRouter()

EXPECTED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

# Helper to convert timeframe string (e.g., "1m", "1h") to milliseconds
# This is duplicated from data_ingestion_service/main.py, consider moving to a shared util
TIMEFRAME_MS_EQUIVALENTS = {
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}

def _timeframe_to_ms(timeframe_str: str) -> Optional[int]:
    return TIMEFRAME_MS_EQUIVALENTS.get(timeframe_str)

@router.get("/klines/{symbol:path}/{timeframe}", response_model=KlineHistoricalResponse, tags=["Kline Data"])
async def get_historical_klines(
    symbol: str,
    timeframe: str,
    start_ms: Optional[int] = Query(None, description="Start timestamp in milliseconds since epoch"),
    end_ms: Optional[int] = Query(None, description="End timestamp in milliseconds since epoch"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of klines to return"),
    db: Session = Depends(get_db)
):
    """
    Fetches historical kline data from TimescaleDB.
    - **symbol**: Trading symbol (e.g., BTCUSDT)
    - **timeframe**: Kline timeframe (e.g., 1m, 1h, 1d)
    - **start_ms**: Optional start timestamp (Unix milliseconds)
    - **end_ms**: Optional end timestamp (Unix milliseconds)
    - **limit**: Maximum number of klines to return (default 1000, max 5000)
    """
    symbol_upper = symbol.upper()
    klines_from_redis: List[KlineRead] = []
    fetch_from_db = True
    
    current_time_ms = int(time.time() * 1000)
    actual_end_ms = end_ms if end_ms is not None else current_time_ms
    
    # Variables for backfill status response
    backfill_status_value: Optional[str] = None
    backfill_last_updated_ts_value: Optional[int] = None
    redis_client_for_status_check = None # Separate client for status check to avoid interference

    try:
        # Check backfill status from Redis
        redis_client_for_status_check = get_redis_connection()
        if redis_client_for_status_check:
            backfill_status_key = f"backfill_status:{symbol_upper}:{timeframe}"
            status_data_raw = await asyncio.to_thread(redis_client_for_status_check.get, backfill_status_key)
            if status_data_raw:
                try:
                    status_data = json.loads(status_data_raw)
                    backfill_status_value = status_data.get("status")
                    backfill_last_updated_ts_value = status_data.get("last_updated_ts")
                    # Optional: Check if last_updated_ts is recent enough to be considered active
                    if backfill_status_value == "in_progress" and backfill_last_updated_ts_value:
                        if (current_time_ms - backfill_last_updated_ts_value * 1000) > (60 * 60 * 1000): # 1 hour threshold
                            logger.warning(f"Backfill status for {symbol_upper}/{timeframe} is 'in_progress' but last update was old. Treating as stale.")
                            backfill_status_value = "stale_in_progress" # Or None
                except json.JSONDecodeError:
                    logger.error(f"Error decoding backfill status from Redis for {backfill_status_key}")
    except Exception as e:
        logger.error(f"Error checking backfill status in Redis: {e}")
    finally:
        if redis_client_for_status_check:
            try:
                await asyncio.to_thread(redis_client_for_status_check.close)
            except Exception as e:
                logger.error(f"Error closing Redis connection for status check: {e}")

    if actual_end_ms >= (current_time_ms - settings.API_REDIS_LOOKBACK_MS):
        redis_client = None
        try:
            redis_client = get_redis_connection()
            if redis_client:
                redis_key = f"klines:{symbol_upper}:{timeframe}"
                
                redis_query_start_ms = start_ms if start_ms is not None else 0
                # Query a slightly wider range in Redis to ensure we capture klines that might start just before API_REDIS_LOOKBACK_MS window
                # but are still relevant if the overall request (start_ms, end_ms) is narrow and recent.
                effective_redis_query_start_ms = max(
                    redis_query_start_ms, 
                    actual_end_ms - settings.MAX_KLINES_IN_REDIS * _timeframe_to_ms(timeframe) - settings.API_REDIS_LOOKBACK_MS # Heuristic
                )

                raw_klines_redis = await asyncio.to_thread(
                    redis_client.zrangebyscore,
                    redis_key,
                    effective_redis_query_start_ms, # Use this calculated start for Redis query
                    actual_end_ms      # Use actual_end_ms for Redis query
                )

                for raw_kline_str in raw_klines_redis:
                    try:
                        kline_dict = json.loads(raw_kline_str)
                        # Filter client-side to match the original start_ms if it was provided
                        if start_ms is not None and kline_dict.get('open_time', 0) < start_ms:
                            continue
                        klines_from_redis.append(KlineRead(**kline_dict))
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding kline from Redis {redis_key}: {e}, data: {raw_kline_str}")
                    except Exception as e: 
                        logger.error(f"Error processing kline from Redis {redis_key}: {e}, data: {kline_dict if 'kline_dict' in locals() else raw_kline_str}")
                
                # Sort Redis results as they might not be perfectly ordered depending on insertion nuances
                klines_from_redis.sort(key=lambda k: k.open_time)
                logger.info(f"Fetched {len(klines_from_redis)} klines from Redis for {symbol_upper}/{timeframe} between {effective_redis_query_start_ms} and {actual_end_ms}")

                if len(klines_from_redis) >= limit and \
                   (start_ms is None or start_ms >= effective_redis_query_start_ms) and \
                   (end_ms is None or end_ms <= actual_end_ms): # Check against actual_end_ms
                    fetch_from_db = False
                
                if klines_from_redis and fetch_from_db:
                    oldest_redis_kline_time = klines_from_redis[0].open_time
                    # Adjust the DB query range: end one interval before the oldest Redis kline
                    # This new end_ms for DB is only used if it's earlier than the original end_ms (or current time if end_ms was None)
                    # and if it's later than or equal to start_ms (if start_ms was provided)
                    potential_db_end_ms = oldest_redis_kline_time - 1 
                    
                    if (end_ms is None or potential_db_end_ms < end_ms) and \
                       (start_ms is None or potential_db_end_ms >= start_ms):
                        end_ms = potential_db_end_ms
                    elif (start_ms is not None and potential_db_end_ms < start_ms): 
                        # If adjusting end_ms makes it earlier than start_ms, no DB query needed for this part
                        fetch_from_db = False


        except Exception as e:
            logger.error(f"Error connecting to or querying Redis: {e}")
        finally:
            if redis_client:
                try:
                    await asyncio.to_thread(redis_client.close) 
                except Exception as e:
                    logger.error(f"Error closing Redis connection: {e}")

    klines_from_db: List[KlineRead] = []
    if fetch_from_db:
        # If end_ms became None due to Redis logic or was already None, and we still need to fetch from DB,
        # it implies we are fetching older data. If start_ms is also None, this case needs careful handling.
        # For now, if end_ms is None after Redis check, it means Redis didn't provide a clear cut-off,
        # so the DB query should proceed with its original end_ms logic (or lack thereof).
        
        db_query_start_ms = start_ms
        db_query_end_ms = end_ms # Use potentially adjusted end_ms from Redis logic

        query = select(Kline).where(
            Kline.symbol == symbol_upper,
            Kline.timeframe == timeframe
        )
        if db_query_start_ms is not None:
            start_dt = datetime.fromtimestamp(db_query_start_ms / 1000.0, tz=timezone.utc)
            query = query.where(Kline.open_time >= start_dt)
        if db_query_end_ms is not None: 
            end_dt = datetime.fromtimestamp(db_query_end_ms / 1000.0, tz=timezone.utc)
            query = query.where(Kline.open_time <= end_dt)
        
        # Determine order for DB query
        # If end_ms is specified (and start_ms is not, or is earlier), fetch latest towards end_ms.
        # Otherwise, fetch oldest from start_ms.
        # MODIFIED: If neither start_ms nor end_ms is given, fetch newest first (default initial load).
        if (db_query_end_ms is not None and (db_query_start_ms is None or db_query_start_ms <= db_query_end_ms)) or \
           (db_query_start_ms is None and db_query_end_ms is None):
            query = query.order_by(desc(Kline.open_time)) # Fetch newest first
            db_ordered_desc = True
        else:
            query = query.order_by(asc(Kline.open_time)) # Fetch oldest first from start_ms
            db_ordered_desc = False

        db_limit = limit - len(klines_from_redis)
        if db_limit > 0:
            query = query.limit(db_limit)
            try:
                result = db.execute(query)
                klines_db_orm = result.scalars().all()
                if db_ordered_desc and klines_db_orm:
                    klines_db_orm.reverse() # Ensure ascending order before combining
                
                for k_orm in klines_db_orm:
                    # Ensure datetime fields from ORM are UTC-aware before validation
                    if k_orm.open_time and k_orm.open_time.tzinfo is None:
                        k_orm.open_time = k_orm.open_time.replace(tzinfo=timezone.utc)
                    if k_orm.close_time and k_orm.close_time.tzinfo is None:
                        k_orm.close_time = k_orm.close_time.replace(tzinfo=timezone.utc)
                    klines_from_db.append(KlineRead.model_validate(k_orm))
                logger.info(f"Fetched {len(klines_from_db)} klines from DB for {symbol_upper}/{timeframe}")
            except Exception as e:
                logger.error(f"Error fetching kline data from DB: {str(e)}")

    combined_klines = klines_from_db + klines_from_redis 
    
    unique_klines_dict: Dict[tuple, KlineRead] = {}
    for k_obj in combined_klines:
        # Ensure that k_obj is an instance of KlineRead or a compatible dict
        # If it's coming from klines_from_redis, it's already KlineRead.
        # If from klines_from_db, it's converted.
        key = (k_obj.symbol, k_obj.timeframe, k_obj.open_time)
        if key not in unique_klines_dict:
            unique_klines_dict[key] = k_obj 
    
    sorted_klines = sorted(list(unique_klines_dict.values()), key=lambda k_sort: k_sort.open_time)
    
    # Final trim to the limit
    final_klines = sorted_klines
    if len(final_klines) > limit:
        # If end_ms is specified (or it's the default initial load where we want latest)
        # and start_ms is not, or if fetching newest first by default (no specific range from client)
        if (end_ms is not None and start_ms is None) or \
           (start_ms is None and end_ms is None and db_ordered_desc): # Rely on db_ordered_desc for default case
            final_klines = sorted_klines[-limit:]
        else:
            # This handles cases where start_ms is specified (fetching oldest first)
            # or a specific range is given and we didn't sort desc by default.
            final_klines = sorted_klines[:limit]

    # Apply start_ms and end_ms filtering on the final list *again* if they were provided
    # This ensures the contract even if upstream data fetching had slight overlaps
    # KlineRead objects in final_klines have open_time as datetime at this stage (before json_encoders)
    if start_ms is not None:
        start_dt_filter = datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc)
        final_klines = [k for k in final_klines if k.open_time >= start_dt_filter]

    if end_ms is not None:
        end_dt_filter = datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc)
        final_klines = [k for k in final_klines if k.open_time <= end_dt_filter]

    if not final_klines:
        logger.info(f"No kline data found for {symbol_upper}/{timeframe} with given parameters.")

    return KlineHistoricalResponse(
        klines=final_klines,
        backfill_status=backfill_status_value,
        backfill_last_updated_ts=backfill_last_updated_ts_value
    )

@router.websocket("/ws/klines/{symbol:path}/{timeframe}")
async def websocket_kline_updates(
    websocket: WebSocket, symbol: str, timeframe: str
):
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for {symbol.upper()}/{timeframe} from {websocket.client.host}. Origin: {websocket.headers.get('origin')}")

    redis_client = None
    pubsub = None
    ping_interval_task = None
    listen_task = None

    try:
        redis_client = get_redis_connection() # Ensure strings are decoded
        if not redis_client:
            logger.error(f"WS ({symbol.upper()}/{timeframe}): Failed to get Redis connection.")
            await websocket.close(code=1011, reason="Internal server error: Redis connection failed")
            return

        # Check if Redis connection is alive
        await asyncio.to_thread(redis_client.ping)
        logger.info(f"WS ({symbol.upper()}/{timeframe}): Successfully connected to Redis and pinged.")

        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        channel_name = f"kline_updates:{symbol.upper()}:{timeframe}"
        await asyncio.to_thread(pubsub.subscribe, channel_name)
        
        logger.info(f"WS ({symbol.upper()}/{timeframe}): Subscribed to Redis channel '{channel_name}'.")
        await websocket.send_json({"status": "subscribed", "channel": channel_name})

        async def listen_to_redis():
            nonlocal pubsub # To ensure we can close it in finally
            try:
                while True:
                    # Check if websocket is still open before blocking on get_message
                    if websocket.client_state != WebSocketState.CONNECTED:
                        logger.info(f"WS ({symbol.upper()}/{timeframe}): WebSocket no longer connected, stopping Redis listener.")
                        break
                    
                    # Use a small timeout to allow the loop to check websocket state periodically
                    message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
                    if message and message.get("type") == "message":
                        kline_data_str = message["data"]
                        # logger.debug(f"WS ({symbol.upper()}/{timeframe}): Received from Redis: {kline_data_str}")
                        try:
                            # Assuming kline_data_str is a JSON string representing a single kline
                            # The frontend expects an array of arrays, or a single kline object to append
                            # The data published by ingestion service is a single kline JSON string
                            kline_obj = json.loads(kline_data_str)
                            await websocket.send_json(kline_obj)
                        except json.JSONDecodeError:
                            logger.error(f"WS ({symbol.upper()}/{timeframe}): Could not decode JSON from Redis: {kline_data_str}")
                        except Exception as e_send:
                            logger.error(f"WS ({symbol.upper()}/{timeframe}): Error sending message to client: {e_send}")
                            # If send fails, client might be gone
                            if websocket.client_state != WebSocketState.CONNECTED: break
                    await asyncio.sleep(0.01) # Small sleep to yield control
            except redis.exceptions.ConnectionError as e_conn:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Redis connection error in listener: {e_conn}. Attempting to close WS.")
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close(code=1011, reason="Redis connection error")
            except Exception as e:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Error in Redis listener: {e}", exc_info=True)
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close(code=1011, reason="Internal server error")
            finally:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): Redis listener task finished.")


        async def send_pings():
            try:
                while True:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        # logger.debug(f"WS ({symbol.upper()}/{timeframe}): Sending ping to client.")
                        await websocket.send_json({"type": "ping", "timestamp": int(time.time() * 1000)})
                    else:
                        logger.info(f"WS ({symbol.upper()}/{timeframe}): WebSocket no longer connected, stopping pinger.")
                        break
                    await asyncio.sleep(settings.WEBSOCKET_PING_INTERVAL_SECONDS) # Use configured interval
            except Exception as e:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Error in pinger task: {e}", exc_info=True)
            finally:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): Pinger task finished.")

        listen_task = asyncio.create_task(listen_to_redis())
        ping_interval_task = asyncio.create_task(send_pings())

        # Keep the main connection open and handle client messages (e.g., explicit close or pong)
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): Client disconnected (detected in main loop).")
                break
            try:
                # Use a timeout to allow checking client_state periodically
                client_message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                # logger.debug(f"WS ({symbol.upper()}/{timeframe}): Received from client: {client_message}")
                if client_message: # process pong or other client messages if needed
                    try:
                        data = json.loads(client_message)
                        if data.get("type") == "pong":
                            # logger.debug(f"WS ({symbol.upper()}/{timeframe}): Received pong from client.")
                            pass # Good, client is alive
                    except json.JSONDecodeError:
                        # logger.debug(f"WS ({symbol.upper()}/{timeframe}): Received non-JSON message: {client_message}")
                        pass # Ignore non-JSON messages for now
            except asyncio.TimeoutError:
                continue # No message from client, continue loop and check state
            except WebSocketDisconnect:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): WebSocketDisconnect received in main loop.")
                break
            except Exception as e:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Error receiving from client: {e}")
                break
        
    except redis.exceptions.ConnectionError as e_conn:
        logger.error(f"WS ({symbol.upper()}/{timeframe}): Initial Redis connection failed: {e_conn}")
        if websocket.client_state == WebSocketState.CONNECTED:
             await websocket.close(code=1011, reason="Internal server error: Redis connection failed")
    except Exception as e:
        logger.error(f"WS ({symbol.upper()}/{timeframe}): General error in WebSocket handler: {e}", exc_info=True)
        if websocket.client_state == WebSocketState.CONNECTED: # Check before trying to close
            await websocket.close(code=1011, reason="Internal server error")
    finally:
        logger.info(f"WS ({symbol.upper()}/{timeframe}): Cleaning up WebSocket connection.")
        if ping_interval_task and not ping_interval_task.done():
            ping_interval_task.cancel()
        if listen_task and not listen_task.done():
            listen_task.cancel()
        
        if pubsub:
            try:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): Unsubscribing and closing PubSub.")
                # Unsubscribe can also be threaded if it blocks
                await asyncio.to_thread(pubsub.unsubscribe) # Unsubscribe from all channels
                await asyncio.to_thread(pubsub.close)
            except Exception as e_ps_close:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Error closing PubSub: {e_ps_close}")
        if redis_client:
            try:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): Closing Redis client connection.")
                await asyncio.to_thread(redis_client.close)
            except Exception as e_rd_close:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Error closing Redis client: {e_rd_close}")

        # Final check on websocket state before attempting to close
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                logger.info(f"WS ({symbol.upper()}/{timeframe}): Ensuring WebSocket is closed in final cleanup.")
                await websocket.close(code=1000)
            except Exception as e_ws_close:
                logger.error(f"WS ({symbol.upper()}/{timeframe}): Error during final WebSocket close: {e_ws_close}")
        logger.info(f"WS ({symbol.upper()}/{timeframe}): WebSocket cleanup finished.")

# --- Temporary Debug Endpoint for Binance WebSocket Outgoing Test ---
@router.get("/debug/test_binance_ws", tags=["Debug"])
async def debug_test_binance_ws():
    binance_ws_url = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
    logger.info(f"[Debug Binance WS] Attempting to connect to: {binance_ws_url}")
    results = {"connection_status": "pending", "messages_received": [], "error": None}

    try:
        async with websockets.connect(binance_ws_url) as websocket_client:
            logger.info(f"[Debug Binance WS] Successfully connected to {binance_ws_url}")
            results["connection_status"] = "connected"
            
            # Receive a few messages
            for i in range(3):
                message = await asyncio.wait_for(websocket_client.recv(), timeout=10.0)
                logger.info(f"[Debug Binance WS] Received message {i+1}: {message}")
                results["messages_received"].append(message)
            
            await websocket_client.close()
            logger.info(f"[Debug Binance WS] Connection closed by client.")
            results["final_status"] = "closed_by_client"

    except websockets.exceptions.InvalidStatusCode as e_status:
        logger.error(f"[Debug Binance WS] Connection failed - Invalid Status Code: {e_status.status_code} - Headers: {e_status.headers}", exc_info=True)
        results["connection_status"] = "failed"
        results["error"] = f"InvalidStatusCode: {e_status.status_code}, Headers: {e_status.headers}"
    except websockets.exceptions.ConnectionClosed as e_closed:
        logger.error(f"[Debug Binance WS] Connection closed unexpectedly: {e_closed}", exc_info=True)
        results["connection_status"] = "failed"
        results["error"] = f"ConnectionClosed: {e_closed}"
    except asyncio.TimeoutError:
        logger.error("[Debug Binance WS] Timeout receiving message.", exc_info=True)
        results["connection_status"] = "timeout_receiving"
        results["error"] = "Timeout receiving message."
    except Exception as e:
        logger.error(f"[Debug Binance WS] An unexpected error occurred: {e}", exc_info=True)
        results["connection_status"] = "failed"
        results["error"] = str(e)
    
    logger.info(f"[Debug Binance WS] Test completed. Results: {results}")
    return results
# --- End Temporary Debug Endpoint ---

@router.post("/upload_csv", tags=["Data Upload"])
async def upload_ohlcv_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # 1. Validate columns
        if not all(col in df.columns for col in EXPECTED_COLUMNS):
            missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
            raise HTTPException(
                status_code=400, 
                detail=f"CSV missing required columns: {', '.join(missing_cols)}. Expected: {', '.join(EXPECTED_COLUMNS)}"
            )
        
        # 2. Keep only expected columns (and in order, though pd.read_csv doesn't guarantee original order for selection)
        df = df[EXPECTED_COLUMNS]

        # 3. Validate data types (basic check for numeric types where expected)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise HTTPException(status_code=400, detail=f"Column '{col}' must contain numeric values.")
        
        # 4. Validate timestamp (convert to datetime and check sort order)
        try:
            if pd.api.types.is_numeric_dtype(df['timestamp']):
                # Timestamps in CSV are numeric and are expected to be in MILLISECONDS
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            else: # Assume it's a date string that pandas can parse
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
            if not df['timestamp'].is_monotonic_increasing:
                raise HTTPException(status_code=400, detail="Timestamps must be sorted in ascending order.")
        except Exception as e:
            # More specific error for timestamp conversion if possible
            raise HTTPException(status_code=400, detail=f"Error processing timestamp column: {str(e)}. Ensure timestamps are in a recognizable format.")

        # For MVP, we can just return the processed data or a success message
        # In a real scenario, you might store this data, associate with a user, etc.
        
        # Convert DataFrame to list of lists (like trading-vue-js expects for chart.data)
        # Assuming timestamp is converted to milliseconds since epoch for JavaScript compatibility
        df['timestamp'] = (df['timestamp'].astype(int) // 10**6) # Convert to milliseconds
        
        # Reorder columns for trading-vue [timestamp, open, high, low, close, volume]
        # This order is already enforced by df = df[EXPECTED_COLUMNS]
        chart_data_list = df.values.tolist()

        return {
            "filename": file.filename,
            "message": "CSV processed successfully.",
            "rowCount": len(df),
            "columns": df.columns.tolist(),
            "chartData": chart_data_list # Send processed data back for immediate use
        }

    except HTTPException as e:
        raise e # Re-raise HTTPExceptions to ensure correct status codes
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
    except Exception as e:
        # Catch-all for other processing errors (e.g., malformed CSV not caught by pandas initially)
        raise HTTPException(status_code=500, detail=f"Error processing CSV file: {str(e)}") 