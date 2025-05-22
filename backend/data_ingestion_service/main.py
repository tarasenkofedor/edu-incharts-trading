import asyncio
import logging
import signal
import os
import sys
import json # Added for Redis operations
import functools # Added for functools.partial
from decimal import Decimal # Added for price/volume precision
import time # Added for gap filling logic
from typing import List, Tuple, Optional # Added Optional
from datetime import datetime, timezone

# Imports assuming execution from project root as 'python -m backend.data_ingestion_service.main'
from backend.app.config import settings
from backend.app.database import SessionLocal, get_db # Assuming SessionLocal is what you meant for db_session_factory
from backend.app.redis_utils import get_redis_connection
from backend.app.models import Kline # Import the Kline model
from sqlalchemy.dialects.postgresql import insert as pg_insert # For ON CONFLICT DO NOTHING
from sqlalchemy.exc import SQLAlchemyError # For DB error handling
from sqlalchemy import select, func as sql_func # Added for DB query

from .service_utils import setup_logging
from .binance_connector import BinanceWebSocketManager
from .historical_data_fetcher import fetch_historical_klines, save_historical_klines_to_db # Added for backfill

logger = logging.getLogger(__name__)

shutdown_event = asyncio.Event()
active_tasks = []

# Timeframe to milliseconds mapping (consider moving to a shared utils if used elsewhere)
TIMEFRAME_MS_EQUIVALENTS = {
    "1s": 1000,
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000, # Approximate month
}

def _timeframe_to_ms(timeframe_str: str) -> Optional[int]:
    """Converts a timeframe string (e.g., '1m', '1h') to milliseconds."""
    return TIMEFRAME_MS_EQUIVALENTS.get(timeframe_str)

async def _get_latest_kline_open_time_from_db(
    symbol: str,
    timeframe: str,
    db_session_factory
) -> Optional[int]:
    """Queries the database for the latest kline open_time for a given symbol and timeframe."""
    db_session = None
    try:
        db_session = db_session_factory()
        stmt = select(sql_func.max(Kline.open_time)).where(
            Kline.symbol == symbol,
            Kline.timeframe == timeframe
        )
        result = await asyncio.to_thread(db_session.execute, stmt)
        latest_open_time = result.scalar_one_or_none()
        if latest_open_time:
            logger.debug(f"[GAP_FILL] Latest open_time in DB for {symbol}/{timeframe}: {latest_open_time}")
            # Convert datetime to millisecond timestamp
            return int(latest_open_time.timestamp() * 1000)
        else:
            logger.debug(f"[GAP_FILL] No kline data found in DB for {symbol}/{timeframe}.")
            return None
    except SQLAlchemyError as e:
        logger.error(f"[GAP_FILL] DB error getting latest kline for {symbol}/{timeframe}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"[GAP_FILL] Unexpected error getting latest kline for {symbol}/{timeframe}: {e}", exc_info=True)
        return None
    finally:
        if db_session:
            await asyncio.to_thread(db_session.close)

# --- End Helper Functions ---

def handle_shutdown_signal(sig, frame):
    logger.warning(f"Received shutdown signal: {sig}. Initiating graceful shutdown.")
    shutdown_event.set()

async def kline_data_processor(kline_data: dict, symbol: str, timeframe: str, redis_client, db_session_factory):
    """
    Processes a single kline data point received from WebSocket.
    - If kline is closed: Saves to TimescaleDB, updates Redis cache, publishes to Redis Pub/Sub.
    - If kline is an update to the unclosed candle: Constructs a kline object representing the
      current state of the forming candle and publishes it to a specific Redis Pub/Sub channel for live ticks.
    """
    try:
        kline_is_closed = kline_data.get('is_closed', False) # Relies on _parse_kline_message correctly setting this
        open_time_ms = int(kline_data['open_time'])
        # Ensure all necessary fields are present for basic processing
        # Price/volume fields will be converted to Decimal later if it's a closed kline
        required_fields = ['open', 'high', 'low', 'close', 'volume', 'close_time']
        if not all(kline_data.get(f) is not None for f in required_fields):
            logger.error(f"[KLINE_PROC] Kline data for {symbol}/{timeframe} OT:{open_time_ms} is missing some required fields for processing. Data: {kline_data}")
            return

    except (KeyError, ValueError) as e:
        logger.error(f"[KLINE_PROC] Error extracting basic fields from kline_data for {symbol}/{timeframe}: {e}. Data: {kline_data}", exc_info=True)
        return

    if kline_is_closed:
        # Process and persist finalized kline (existing logic)
        try:
            kline_obj = Kline(
                symbol=symbol,
                timeframe=timeframe,
                open_time=datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc),
                open_price=Decimal(str(kline_data['open'])),
                high_price=Decimal(str(kline_data['high'])),
                low_price=Decimal(str(kline_data['low'])),
                close_price=Decimal(str(kline_data['close'])),
                volume=Decimal(str(kline_data['volume'])),
                close_time=datetime.fromtimestamp(int(kline_data['close_time']) / 1000, tz=timezone.utc),
                quote_asset_volume=Decimal(str(kline_data['quote_asset_volume'])),
                number_of_trades=int(kline_data['number_of_trades']),
                taker_buy_base_asset_volume=Decimal(str(kline_data['taker_buy_base_asset_volume'])),
                taker_buy_quote_asset_volume=Decimal(str(kline_data['taker_buy_quote_asset_volume']))
            )
        except (KeyError, ValueError) as e:
            logger.error(f"[KLINE_PROC] Error creating Kline ORM object for closed kline {symbol}/{timeframe}: {e}. Data: {kline_data}", exc_info=True)
            return

        logger.debug(f"[KLINE_PROC] Processing closed kline for {symbol}/{timeframe}: OT {kline_obj.open_time} C {kline_obj.close_price} V {kline_obj.volume}")

        # 1. Save to TimescaleDB (existing logic)
        db_session = None
        save_successful_or_conflict = False
        try:
            db_session = db_session_factory()
            stmt = pg_insert(Kline).values(
                symbol=kline_obj.symbol, timeframe=kline_obj.timeframe, open_time=kline_obj.open_time,
                open_price=kline_obj.open_price, high_price=kline_obj.high_price, low_price=kline_obj.low_price,
                close_price=kline_obj.close_price, volume=kline_obj.volume, close_time=kline_obj.close_time,
                quote_asset_volume=kline_obj.quote_asset_volume, number_of_trades=kline_obj.number_of_trades,
                taker_buy_base_asset_volume=kline_obj.taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume=kline_obj.taker_buy_quote_asset_volume
            ).on_conflict_do_nothing(index_elements=['symbol', 'timeframe', 'open_time'])
            result = await asyncio.to_thread(db_session.execute, stmt)
            await asyncio.to_thread(db_session.commit)
            if result.rowcount > 0:
                logger.info(f"[DB_SAVE] Closed kline {symbol}/{timeframe} OT:{kline_obj.open_time} inserted.")
            else:
                logger.debug(f"[DB_SAVE] Closed kline {symbol}/{timeframe} OT:{kline_obj.open_time} already exists (conflict).")
            save_successful_or_conflict = True
        except SQLAlchemyError as e:
            logger.error(f"[DB_SAVE] SQLAlchemyError saving closed kline {symbol}/{timeframe} OT:{kline_obj.open_time}: {e}", exc_info=True)
            if db_session: await asyncio.to_thread(db_session.rollback)
        except Exception as e:
            logger.error(f"[DB_SAVE] Unexpected error saving closed kline {symbol}/{timeframe} OT:{kline_obj.open_time}: {e}", exc_info=True)
            if db_session: await asyncio.to_thread(db_session.rollback)
        finally:
            if db_session: await asyncio.to_thread(db_session.close)

        if not save_successful_or_conflict:
            logger.warning(f"[KLINE_PROC] Aborting Redis ops for closed kline {symbol}/{timeframe} OT:{kline_obj.open_time} due to DB save failure.")
            return

        # 2. Update Redis Cache (Sorted Set) for closed kline (existing logic)
        redis_key_ohlcv = f"klines:{symbol}:{timeframe}"
        kline_for_redis_ohlcv = {
            'open_time': open_time_ms,
            'open': str(kline_obj.open_price), 'high': str(kline_obj.high_price),
            'low': str(kline_obj.low_price), 'close': str(kline_obj.close_price),
            'volume': str(kline_obj.volume),
            'close_time': int(kline_data['close_time']),
            'is_closed': True # Explicitly True for this path
        }
        kline_json_for_redis_ohlcv = json.dumps(kline_for_redis_ohlcv)
        try:
            score = kline_obj.open_time.timestamp()
            await asyncio.to_thread(redis_client.zadd, redis_key_ohlcv, {kline_json_for_redis_ohlcv: score})
            logger.debug(f"[REDIS_CACHE] Added closed kline to ZSET {redis_key_ohlcv}: Score {score}")
            # Trim the sorted set to MAX_KLINES_IN_REDIS (existing logic)
            # Retain (MAX_KLINES_IN_REDIS - 1) to remove elements from the beginning (older ones)
            # zremrangebyrank key 0 -(MAX_KLINES_IN_REDIS + 1) would be more correct for keeping newest N if sorted by score ASC
            # Or, if MAX_KLINES_IN_REDIS is, e.g., 2000, and scores are timestamps (ascending):
            # Keep elements from rank -MAX_KLINES_IN_REDIS to -1 (the newest MAX_KLINES_IN_REDIS elements).
            # So, remove elements from rank 0 to -(MAX_KLINES_IN_REDIS + 1) (everything OLDER than the newest MAX_KLINES_IN_REDIS).
            # Or, simpler: if zcard > MAX_KLINES_IN_REDIS, zremrangebyrank 0 (zcard - MAX_KLINES_IN_REDIS -1)
            # Current logic from settings: MAX_KLINES_IN_REDIS
            # To keep the newest `max_klines`, if sorted ascending by score (timestamp), remove from rank 0 to `count - max_klines - 1`.
            # Or, using negative indices (which count from the end, highest score first if sorted asc):
            # remove elements from rank 0 up to `count - settings.MAX_KLINES_IN_REDIS -1`
            # `redis_client.zremrangebyrank(redis_key, 0, -settings.MAX_KLINES_IN_REDIS -1)` is likely what was intended for trimming.
            # The original `zremrangebyrank(redis_key, 0, settings.MAX_KLINES_IN_REDIS -1)` would keep only the oldest elements if the count is > MAX_KLINES_IN_REDIS
            # Correct logic for keeping newest N items:
            # await asyncio.to_thread(redis_client.zremrangebyrank, redis_key, 0, - (settings.MAX_KLINES_IN_REDIS + 1))
            # This keeps the items from -MAX_KLINES_IN_REDIS to -1 (the newest MAX_KLINES_IN_REDIS items)
            # Safest trim: check count, then trim if over.
            current_count = await asyncio.to_thread(redis_client.zcard, redis_key_ohlcv)
            if current_count > settings.MAX_KLINES_IN_REDIS:
                # Remove the oldest entries to maintain MAX_KLINES_IN_REDIS
                # Number to remove = current_count - MAX_KLINES_IN_REDIS
                # Remove from rank 0 (oldest) to (number_to_remove - 1)
                num_to_remove = current_count - settings.MAX_KLINES_IN_REDIS
                await asyncio.to_thread(redis_client.zremrangebyrank, redis_key_ohlcv, 0, num_to_remove - 1)
                logger.debug(f"[REDIS_CACHE] Trimmed ZSET {redis_key_ohlcv} to ~{settings.MAX_KLINES_IN_REDIS} items. Removed {num_to_remove}.")

        except Exception as e:
            logger.error(f"[REDIS_CACHE] Error updating Redis cache for closed kline {symbol}/{timeframe} OT:{kline_obj.open_time}: {e}", exc_info=True)

        # 3. Publish to Redis Pub/Sub for closed kline (existing logic)
        pubsub_channel_closed = f"kline_updates:{symbol}:{timeframe}"
        payload_closed = {
            "type": "kline_closed",
            "data": kline_for_redis_ohlcv # Use the same structure as for Redis cache
        }
        try:
            await asyncio.to_thread(redis_client.publish, pubsub_channel_closed, json.dumps(payload_closed))
            logger.info(f"[REDIS_PUB] Published closed kline to {pubsub_channel_closed} for {symbol}/{timeframe} OT:{open_time_ms}")
        except Exception as e:
            logger.error(f"[REDIS_PUB] Error publishing closed kline to {pubsub_channel_closed} for {symbol}/{timeframe} OT:{open_time_ms}: {e}", exc_info=True)

    else:
        # Process unclosed kline update (tick)
        logger.debug(f"[KLINE_PROC] Processing unclosed (tick) kline for {symbol}/{timeframe} OT:{open_time_ms} C:{kline_data['close']}")
        
        # Construct the kline data for the current tick update
        # This represents the current state of the forming candle
        # Timestamps should be in milliseconds as expected by frontend/DataCube
        current_tick_kline_data = {
            'event_type': kline_data.get('event_type'), # from _parse_kline_message
            'event_time': kline_data.get('event_time'), # from _parse_kline_message
            'symbol': symbol,
            'timeframe': timeframe,
            'open_time': open_time_ms,
            'open': str(kline_data['open']), # Use string for consistency, Decimal not needed for pub/sub if frontend handles string
            'high': str(kline_data['high']),
            'low': str(kline_data['low']),
            'close': str(kline_data['close']),
            'volume': str(kline_data['volume']),
            'close_time': int(kline_data['close_time']), # This is the expected end time of the interval
            'quote_asset_volume': str(kline_data['quote_asset_volume']),
            'number_of_trades': int(kline_data['number_of_trades']),
            'is_closed': False, # Explicitly False for this path
            'taker_buy_base_asset_volume': str(kline_data['taker_buy_base_asset_volume']),
            'taker_buy_quote_asset_volume': str(kline_data['taker_buy_quote_asset_volume'])
        }

        # Publish to a specific Redis Pub/Sub channel for live ticks
        # Option 1: Different channel name
        # pubsub_channel_tick = f"kline_live_tick:{symbol}:{timeframe}"
        # Option 2: Same channel, different message type (chosen here for simplicity on subscriber side initially)
        pubsub_channel_tick = f"kline_updates:{symbol}:{timeframe}"
        payload_tick = {
            "type": "kline_tick", # Differentiate from "kline_closed"
            "data": current_tick_kline_data
        }

        try:
            await asyncio.to_thread(redis_client.publish, pubsub_channel_tick, json.dumps(payload_tick))
            logger.debug(f"[REDIS_PUB_TICK] Published live tick to {pubsub_channel_tick} for {symbol}/{timeframe} OT:{open_time_ms} C:{current_tick_kline_data['close']}")
        except Exception as e:
            logger.error(f"[REDIS_PUB_TICK] Error publishing live tick to {pubsub_channel_tick} for {symbol}/{timeframe} OT:{open_time_ms}: {e}", exc_info=True)

async def run_service():
    """Main function to run the data ingestion service."""
    # Setup logging
    # Configure logging level based on settings
    # setup_logging(level=logging.INFO if not settings.DEBUG_MODE else logging.DEBUG)
    setup_logging(level=logging.INFO) # Simplified logging setup

    logger.info("Data Ingestion Service starting...")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    # Initialize Redis connection
    redis_client = None
    try:
        redis_client = get_redis_connection()
        if redis_client:
            logger.info("Successfully connected to Redis for Ingestion Service.")
        else:
            logger.error("Failed to connect to Redis for Ingestion Service. Exiting.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Critical error initializing Redis connection: {e}. Exiting.", exc_info=True)
        sys.exit(1)
        
    # DB Session Factory
    db_session_factory = SessionLocal

    # --- Proactive Symbol/Timeframe Tracking & Gap Filling ---
    proactive_symbols_list = [s.strip().upper() for s in settings.PROACTIVE_SYMBOLS.split(',') if s.strip()]
    proactive_timeframes_list = [tf.strip() for tf in settings.PROACTIVE_TIMEFRAMES.split(',') if tf.strip()]
    proactive_pairs: List[Tuple[str, str]] = []

    if proactive_symbols_list and proactive_timeframes_list:
        for symbol_str in proactive_symbols_list:
            for tf_str in proactive_timeframes_list:
                if not TIMEFRAME_MS_EQUIVALENTS.get(tf_str): # Validate timeframe
                    logger.warning(f"[CONFIG] Invalid timeframe '{tf_str}' in PROACTIVE_TIMEFRAMES. Skipping pair {symbol_str}/{tf_str}.")
                    continue
                proactive_pairs.append((symbol_str, tf_str))
        logger.info(f"Proactively tracking {len(proactive_pairs)} pairs: {proactive_pairs}")

        # Initial Gap Filling for proactive pairs
        for pair_symbol, pair_timeframe in proactive_pairs:
            if shutdown_event.is_set():
                logger.info("Shutdown initiated, skipping further gap fills.")
                break
            
            logger.info(f"[GAP_FILL] Checking/Initiating gap fill for {pair_symbol}/{pair_timeframe}...")
            backfill_status_key = f"backfill_status:{pair_symbol}:{pair_timeframe}"
            try:
                # Set backfill status in Redis
                if redis_client:
                    await asyncio.to_thread(
                        redis_client.setex,
                        backfill_status_key,
                        3600, # Expires in 1 hour, to auto-clear if service crashes mid-backfill
                        json.dumps({"status": "in_progress_startup", "last_updated_ts": int(time.time())})
                    )

                latest_db_open_time = await _get_latest_kline_open_time_from_db(pair_symbol, pair_timeframe, db_session_factory)
                interval_ms = _timeframe_to_ms(pair_timeframe)
                
                if not interval_ms:
                    logger.error(f"[GAP_FILL] Invalid timeframe {pair_timeframe} for {pair_symbol}. Cannot determine interval_ms. Skipping gap fill.")
                    await asyncio.to_thread(redis_client.set, backfill_status_key, json.dumps({"status": "error_invalid_timeframe", "last_updated_ts": int(time.time())}), ex=3600)
                    continue

                current_target_time_ms = int(time.time() * 1000) - (settings.HISTORICAL_FETCH_BUFFER_KLINES * interval_ms)

                if latest_db_open_time is None:
                    # No data exists, backfill for INITIAL_BACKFILL_DAYS
                    start_backfill_ms = int(time.time() * 1000) - (settings.INITIAL_BACKFILL_DAYS * 24 * 60 * 60 * 1000)
                    logger.info(f"[GAP_FILL] No data for {pair_symbol}/{pair_timeframe}. Backfilling from {datetime.fromtimestamp(start_backfill_ms/1000)} to now.")
                    fetched_count, failed_count = await fetch_historical_klines_and_save(pair_symbol, pair_timeframe, start_backfill_ms, current_target_time_ms, db_session_factory)
                    logger.info(f"[GAP_FILL] Initial backfill for {pair_symbol}/{pair_timeframe} complete. Fetched: {fetched_count}, Failed: {failed_count}")
                elif latest_db_open_time < (current_target_time_ms - interval_ms): # Check if there's a significant gap
                    # Data exists, but there's a gap
                    start_backfill_ms = latest_db_open_time + interval_ms # Start from the next expected kline
                    logger.info(f"[GAP_FILL] Gap detected for {pair_symbol}/{pair_timeframe}. Latest in DB: {datetime.fromtimestamp(latest_db_open_time/1000)}. Backfilling from {datetime.fromtimestamp(start_backfill_ms/1000)} to {datetime.fromtimestamp(current_target_time_ms/1000)}.")
                    fetched_count, failed_count = await fetch_historical_klines_and_save(pair_symbol, pair_timeframe, start_backfill_ms, current_target_time_ms, db_session_factory)
                    logger.info(f"[GAP_FILL] Gap fill for {pair_symbol}/{pair_timeframe} complete. Fetched: {fetched_count}, Failed: {failed_count}")
                else:
                    logger.info(f"[GAP_FILL] No significant gap found for {pair_symbol}/{pair_timeframe}. Latest data is recent enough.")
                
                # Mark backfill as completed in Redis (or clear it)
                await asyncio.to_thread(redis_client.set, backfill_status_key, json.dumps({"status": "completed_startup", "last_updated_ts": int(time.time())}), ex=3600)

            except Exception as e_gapfill:
                logger.error(f"[GAP_FILL] Error during gap fill for {pair_symbol}/{pair_timeframe}: {e_gapfill}", exc_info=True)
                backfill_status_key = f"backfill_status:{pair_symbol}:{pair_timeframe}"
                await asyncio.to_thread(redis_client.set, backfill_status_key, json.dumps({"status": "error_during_startup_fill", "last_updated_ts": int(time.time())}), ex=3600)

            # Create and start BinanceWebSocketManager for this pair
            manager = BinanceWebSocketManager(
                symbol=pair_symbol,
                timeframe=pair_timeframe,
                data_handler_callback=functools.partial(kline_data_processor, symbol=pair_symbol, timeframe=pair_timeframe, redis_client=redis_client, db_session_factory=db_session_factory),
                shutdown_event_global=shutdown_event # Pass the global shutdown event
            )
            task = asyncio.create_task(manager.run())
            active_tasks.append(task)
            logger.info(f"Scheduled WebSocket manager for {pair_symbol}/{pair_timeframe}.")
    else:
        logger.warning("PROACTIVE_SYMBOLS or PROACTIVE_TIMEFRAMES not configured. No live data will be ingested.")

    # --- Start WebSocket Managers for Proactive Pairs ---
    if proactive_pairs:
        logger.info(f"All {len(active_tasks)} WebSocket managers scheduled. Service is running and waiting for shutdown signal...")
        
        # Wait for the shutdown signal
        await shutdown_event.wait()
        logger.info("Shutdown signal received. Proceeding to stop tasks.")

        # Signal all WebSocket managers to stop (they should observe shutdown_event_global)
        # The BinanceWebSocketManager's run loop should exit when shutdown_event is set.
        # We still cancel them to be sure and to handle any that might be stuck.
        
        for task in active_tasks:
            if not task.done():
                logger.info(f"Cancelling task {task.get_name()}...")
                task.cancel()
        
        if active_tasks:
            logger.info(f"Awaiting cancellation of {len(active_tasks)} tasks...")
            results = await asyncio.gather(*active_tasks, return_exceptions=True)
            logger.info("All active tasks have been processed after cancellation.")
            for i, result in enumerate(results):
                if isinstance(result, asyncio.CancelledError):
                    logger.debug(f"Task {active_tasks[i].get_name()} was cancelled successfully.")
                elif isinstance(result, Exception):
                    logger.error(f"Task {active_tasks[i].get_name()} raised an exception during shutdown: {result}", exc_info=result)
                # else: (task completed normally before cancellation, or after)
                    # logger.debug(f"Task {active_tasks[i].get_name()} completed with result: {result}")

    else: # No active tasks, just wait for shutdown
        logger.info("Service is idle (no proactive pairs). Waiting for shutdown signal.")
        await shutdown_event.wait()

    logger.info("Shutting down InChart Data Ingestion Service.")
    if redis_client:
        try:
            logger.info("Closing Redis connection...")
            await asyncio.to_thread(redis_client.close) # Ensure close is synchronous if needed, or use async client's close
            logger.info("Redis connection closed.")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}", exc_info=True)
    
    logger.info("Service shutdown complete.")
    sys.exit(0)

async def fetch_historical_klines_and_save(symbol, timeframe, start_ms, end_ms, db_factory):
    """Helper to fetch and save, used by gap filling."""
    try:
        klines_models = await fetch_historical_klines(symbol, timeframe, start_ms, end_ms)
        if klines_models:
            saved_count, failed_count = await save_historical_klines_to_db(klines_models, db_factory)
            return saved_count, failed_count
        return 0, 0
    except Exception as e:
        logger.error(f"[HIST_SAVE_HELPER] Error in fetch_historical_klines_and_save for {symbol}/{timeframe}: {e}", exc_info=True)
        return 0, 0

if __name__ == "__main__":
    # This allows running the service directly, e.g., `python -m backend.data_ingestion_service.main`
    # Ensure PYTHONPATH includes the project root for `backend.app` imports
    # Example: PYTHONPATH=$PYTHONPATH:/path/to/your/project
    # Or run from `backend/` directory: `python -m data_ingestion_service.main`
    
    # Basic check to see if .env might be loaded by Pydantic settings
    if not settings.DATABASE_URL:
        print("ERROR: DATABASE_URL not found in settings. Ensure .env is configured and readable.", file=sys.stderr)
        sys.exit(1)
    
    try:
        asyncio.run(run_service())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Setting shutdown event.")
        shutdown_event.set()
        # Allow ongoing run_service to handle graceful shutdown via the event.
        # Depending on where KeyboardInterrupt is caught, direct sys.exit might be too abrupt.
        # The signal handlers for SIGINT/SIGTERM should set the event.
    except Exception as e:
        logger.critical(f"Unhandled exception in service runner: {e}", exc_info=True)
        sys.exit(1) 