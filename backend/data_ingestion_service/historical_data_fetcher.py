import asyncio
import httpx
import logging
import time
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.models import Kline
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from backend.app.database import SessionLocal # Assuming SessionLocal is the factory

logger = logging.getLogger(__name__)

BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/klines"
# Alternative if needed: https://data.binance.com for public data, might have different limits

# Binance API constants
MAX_KLINES_PER_REQUEST = 1000
# Rate Limits: 1200 requests per minute; 10 orders per second; 20 orders per 10 seconds.
# We should be conservative. Let's aim for max 1 request every 2 seconds initially if unauthenticated.
# If authenticated, limits might be higher.
DEFAULT_REQUEST_DELAY_SECONDS = 2 # Delay between batches of requests
RETRY_ATTEMPTS = 5
INITIAL_RETRY_DELAY_SECONDS = 5
MAX_RETRY_DELAY_SECONDS = 60
RETRY_MULTIPLIER = 2

# Mapping from our timeframe strings to Binance API interval strings
TIMEFRAME_TO_BINANCE_INTERVAL = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M",
}


def _map_binance_kline_to_model(binance_kline: list, symbol: str, timeframe: str) -> Optional[Kline]:
    """Maps a single kline list from Binance API to our Kline model object."""
    try:
        # Binance kline format:
        # [
        #   1499040000000,      // 0 Kline open time
        #   "0.01634790",       // 1 Open price
        #   "0.80000000",       // 2 High price
        #   "0.01575800",       // 3 Low price
        #   "0.01577100",       // 4 Close price
        #   "148976.11427815",  // 5 Volume
        #   1499644799999,      // 6 Kline close time
        #   "2434.19055334",    // 7 Quote asset volume
        #   308,                // 8 Number of trades
        #   "1756.87402397",    // 9 Taker buy base asset volume
        #   "28.46694368",      // 10 Taker buy quote asset volume
        #   "0"                 // 11 Ignore
        # ]
        return Kline(
            symbol=symbol,
            timeframe=timeframe,
            open_time=datetime.fromtimestamp(int(binance_kline[0]) / 1000, tz=timezone.utc),
            open_price=Decimal(str(binance_kline[1])),
            high_price=Decimal(str(binance_kline[2])),
            low_price=Decimal(str(binance_kline[3])),
            close_price=Decimal(str(binance_kline[4])),
            volume=Decimal(str(binance_kline[5])),
            close_time=datetime.fromtimestamp(int(binance_kline[6]) / 1000, tz=timezone.utc),
            quote_asset_volume=Decimal(str(binance_kline[7])),
            number_of_trades=int(binance_kline[8]),
            taker_buy_base_asset_volume=Decimal(str(binance_kline[9])),
            taker_buy_quote_asset_volume=Decimal(str(binance_kline[10])),
            # is_closed=True  # Removed: Kline ORM model does not have this field
        )
    except (IndexError, ValueError, TypeError) as e:
        logger.error(f"[HIST_FETCHER] Error mapping Binance kline to model: {e}. Data: {binance_kline}", exc_info=True)
        return None

async def fetch_historical_klines(
    symbol: str,
    timeframe: str,
    start_time_ms: int,
    end_time_ms: Optional[int] = None,
    limit_per_api_call: int = MAX_KLINES_PER_REQUEST
) -> List[Kline]:
    """
    Fetches historical kline data from Binance REST API for a given symbol and timeframe.

    Args:
        symbol: Trading symbol (e.g., BTCUSDT).
        timeframe: Kline timeframe (e.g., "1m", "1h", "1d").
        start_time_ms: Start timestamp in milliseconds.
        end_time_ms: End timestamp in milliseconds (optional, defaults to current time if not provided by Binance).
                     If provided, fetching stops once klines pass this time.
        limit_per_api_call: Number of klines to fetch per API call (max 1000 for Binance).

    Returns:
        A list of Kline model instances, or an empty list if fetching fails or no data.
    """
    binance_interval = TIMEFRAME_TO_BINANCE_INTERVAL.get(timeframe)
    if not binance_interval:
        logger.error(f"[HIST_FETCHER] Invalid timeframe: {timeframe}. Cannot map to Binance interval.")
        return []

    all_klines_models: List[Kline] = []
    current_start_time_ms = start_time_ms
    request_delay = DEFAULT_REQUEST_DELAY_SECONDS
    
    # Convert end_time_ms to datetime object if it exists, for proper comparison
    end_time_dt: Optional[datetime] = None
    if end_time_ms is not None:
        end_time_dt = datetime.fromtimestamp(end_time_ms / 1000, tz=timezone.utc)

    # Prepare headers - API key might increase rate limits or access
    headers = {}
    if settings.BINANCE_API_KEY:
        headers['X-MBX-APIKEY'] = settings.BINANCE_API_KEY
        # Note: Secret key is not used for GET /api/v3/klines, only for signed endpoints.

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {
                "symbol": symbol.upper(),
                "interval": binance_interval,
                "startTime": current_start_time_ms,
                "limit": min(limit_per_api_call, MAX_KLINES_PER_REQUEST) # Ensure we don't exceed Binance max
            }
            if end_time_ms:
                params["endTime"] = end_time_ms
            
            logger.info(f"[HIST_FETCHER] Fetching klines for {symbol}/{timeframe} from {current_start_time_ms}" +
                        (f" to {end_time_ms}" if end_time_ms else f" limit {params['limit']}"))

            retry_count = 0
            current_retry_delay = INITIAL_RETRY_DELAY_SECONDS
            response_data = None

            while retry_count < RETRY_ATTEMPTS:
                try:
                    response = await client.get(BINANCE_SPOT_API_URL, params=params, headers=headers)
                    response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
                    response_data = response.json()
                    break # Success
                except httpx.HTTPStatusError as e:
                    logger.warning(f"[HIST_FETCHER] HTTP error fetching {symbol}/{timeframe}: {e.response.status_code} - {e.response.text}")
                    if e.response.status_code in [429, 418]: # Rate limit or IP ban
                        logger.warning(f"[HIST_FETCHER] Rate limit hit. Retrying in {current_retry_delay}s...")
                        await asyncio.sleep(current_retry_delay)
                        current_retry_delay = min(current_retry_delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY_SECONDS)
                        retry_count += 1
                    else: # Other HTTP errors (e.g., 400 for bad symbol)
                        logger.error(f"[HIST_FETCHER] Unrecoverable HTTP error for {symbol}/{timeframe}. Aborting fetch for this batch.")
                        return all_klines_models # Return what we have so far
                except httpx.RequestError as e: # Network errors, timeouts
                    logger.warning(f"[HIST_FETCHER] Request error for {symbol}/{timeframe}: {e}. Retrying in {current_retry_delay}s...")
                    await asyncio.sleep(current_retry_delay)
                    current_retry_delay = min(current_retry_delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY_SECONDS)
                    retry_count += 1
                except json.JSONDecodeError as e:
                    logger.error(f"[HIST_FETCHER] JSON decode error for {symbol}/{timeframe}: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
                    return all_klines_models # Unlikely, but good to handle

            if not response_data:
                logger.error(f"[HIST_FETCHER] Failed to fetch data for {symbol}/{timeframe} after {RETRY_ATTEMPTS} retries. Aborting.")
                return all_klines_models # Return what we have so far

            if not isinstance(response_data, list) or not response_data:
                logger.info(f"[HIST_FETCHER] No more kline data returned for {symbol}/{timeframe} from {current_start_time_ms}.")
                break # No more data

            batch_klines_models: List[Kline] = []
            last_kline_open_time_ms = 0
            for kline_item in response_data:
                kline_model = _map_binance_kline_to_model(kline_item, symbol, timeframe)
                if kline_model:
                    # Ensure we don't go past end_time_dt if specified and data is inclusive of it
                    if end_time_dt and kline_model.open_time >= end_time_dt:
                        logger.info(f"[HIST_FETCHER] Reached specified end_time ({end_time_dt}) for {symbol}/{timeframe}. Stopping fetch.")
                        response_data = [] # Signal to break outer loop
                        break 
                    batch_klines_models.append(kline_model)
                    # last_kline_open_time_ms should store the integer ms timestamp for the next API call
                    last_kline_open_time_ms = int(kline_model.open_time.timestamp() * 1000) 
            
            all_klines_models.extend(batch_klines_models)
            logger.info(f"[HIST_FETCHER] Fetched {len(batch_klines_models)} klines for {symbol}/{timeframe}. Total: {len(all_klines_models)}.")

            if len(response_data) < params['limit']: # Fewer klines than limit means we reached the end for this period
                logger.info(f"[HIST_FETCHER] Fetched fewer klines ({len(response_data)}) than limit ({params['limit']}). Assuming end of available data for {symbol}/{timeframe}.")
                break
            
            if not batch_klines_models: # If after filtering (e.g. by end_time_ms) no klines were added
                logger.info(f"[HIST_FETCHER] No new klines added to batch for {symbol}/{timeframe}, likely due to end_time_ms filter. Stopping fetch.")
                break

            # The next query's startTime should be the open_time of the last kline received + 1ms.
            # Example: if last kline's open_time is T (in ms), next startTime is T + 1.
            # This is to avoid re-fetching the last kline.
            if not last_kline_open_time_ms: # Should only happen if response_data was empty from start or all items failed mapping
                logger.warning(f"[HIST_FETCHER] last_kline_open_time_ms is not set after processing a batch for {symbol}/{timeframe}. This might indicate an issue or end of data.")
                break
            current_start_time_ms = last_kline_open_time_ms + 1 

            # Respectful delay before next API call
            logger.debug(f"[HIST_FETCHER] Waiting {request_delay}s before next fetch for {symbol}/{timeframe}...")
            await asyncio.sleep(request_delay)

    logger.info(f"[HIST_FETCHER] Finished fetching historical klines for {symbol}/{timeframe}. Total fetched: {len(all_klines_models)}.")
    return all_klines_models


async def save_historical_klines_to_db(
    klines: List[Kline],
    db_session_factory # Typically SessionLocal
) -> tuple[int, int]:
    """
    Saves a list of Kline model instances to the TimescaleDB using ON CONFLICT DO NOTHING.

    Args:
        klines: A list of Kline model instances.
        db_session_factory: A callable that provides a new SQLAlchemy session.

    Returns:
        A tuple (inserted_count, conflicted_count).
    """
    if not klines:
        return 0, 0

    inserted_count = 0
    conflicted_count = 0
    
    # Batching might be more efficient for very large lists, but ON CONFLICT handles duplicates well.
    # For simplicity, let's insert them one by one using the model objects,
    # or prepare a list of dicts for a single bulk insert statement.
    # Using bulk_insert_mappings for efficiency with on_conflict_do_nothing.

    kline_mappings = [
        {
            "symbol": k.symbol,
            "timeframe": k.timeframe,
            "open_time": k.open_time,
            "open_price": k.open_price,
            "high_price": k.high_price,
            "low_price": k.low_price,
            "close_price": k.close_price,
            "volume": k.volume,
            "close_time": k.close_time,
            "quote_asset_volume": k.quote_asset_volume,
            "number_of_trades": k.number_of_trades,
            "taker_buy_base_asset_volume": k.taker_buy_base_asset_volume,
            "taker_buy_quote_asset_volume": k.taker_buy_quote_asset_volume
            # "is_closed" field removed as it's not in the Kline ORM model
        } for k in klines
    ]

    db_session = None
    try:
        db_session = db_session_factory()
        
        # Using SQLAlchemy's insert with on_conflict_do_nothing
        stmt = pg_insert(Kline).values(kline_mappings)
        stmt = stmt.on_conflict_do_nothing(index_elements=['symbol', 'timeframe', 'open_time'])
        
        # To get a count of inserted vs conflicted, we might need to execute differently or check result.
        # For now, execute and assume conflicts are handled silently by DB.
        # The `result.rowcount` from `execute(stmt)` when using `on_conflict_do_nothing`
        # typically returns the number of rows *affected* by the INSERT, which means newly inserted rows.
        
        result = await asyncio.to_thread(db_session.execute, stmt)
        await asyncio.to_thread(db_session.commit)
        
        inserted_count = result.rowcount if result else 0 # Number of new rows inserted
        conflicted_count = len(klines) - inserted_count # Estimate of conflicted rows

        logger.info(f"[DB_SAVE] Saved historical klines. Inserted: {inserted_count}, Conflicts/Skipped: {conflicted_count} (Total attempted: {len(klines)})")

    except SQLAlchemyError as e:
        logger.error(f"[DB_SAVE] SQLAlchemyError saving historical klines: {e}", exc_info=True)
        if db_session: await asyncio.to_thread(db_session.rollback)
        return 0, len(klines) # Assume all failed if error during batch
    except Exception as e:
        logger.error(f"[DB_SAVE] Unexpected error saving historical klines: {e}", exc_info=True)
        if db_session: await asyncio.to_thread(db_session.rollback)
        return 0, len(klines)
    finally:
        if db_session: await asyncio.to_thread(db_session.close)
            
    return inserted_count, conflicted_count


if __name__ == "__main__":
    # Example Usage (for testing this module directly)
    async def main_test():
        from backend.data_ingestion_service.service_utils import setup_logging
        setup_logging(level=logging.DEBUG)

        # Configure .env properly with BINANCE_API_KEY for potentially better rate limits
        # Ensure your DB is running and accessible via DATABASE_URL in .env
        
        # Test fetching
        test_symbol = "BTCUSDT"
        test_timeframe = "1m"
        # Fetch ~1 day of 1m klines (1440 minutes)
        # Start time: e.g., 2 days ago from now
        now_ms = int(time.time() * 1000)
        start_fetch_ms = now_ms - (2 * 24 * 60 * 60 * 1000) # 2 days ago
        end_fetch_ms = now_ms - (1 * 24 * 60 * 60 * 1000) # 1 day ago
        
        # More focused test: Fetch last 30 minutes of 1m data
        # start_fetch_ms = now_ms - (35 * 60 * 1000) # 35 mins ago
        # end_fetch_ms = now_ms - (5 * 60 * 1000)   # 5 mins ago


        logger.info(f"--- Starting historical fetch test for {test_symbol}/{test_timeframe} ---")
        fetched_klines = await fetch_historical_klines(
            symbol=test_symbol,
            timeframe=test_timeframe,
            start_time_ms=start_fetch_ms,
            end_time_ms=end_fetch_ms, # Optional: fetch up to this point
            limit_per_api_call=500 # Test with a smaller limit per call
        )

        if fetched_klines:
            logger.info(f"--- Successfully fetched {len(fetched_klines)} klines ---")
            # for k in fetched_klines[:3]: # Print first 3
            #     logger.info(f"Kline: {k.symbol} {k.timeframe} OT:{k.open_time} O:{k.open_price} C:{k.close_price} V:{k.volume} CT:{k.close_time}")
            
            # Test saving to DB
            logger.info(f"--- Attempting to save {len(fetched_klines)} klines to DB ---")
            inserted, conflicted = await save_historical_klines_to_db(fetched_klines, SessionLocal)
            logger.info(f"--- DB Save complete. Inserted: {inserted}, Conflicted/Skipped: {conflicted} ---")
        else:
            logger.warning(f"--- No klines fetched for {test_symbol}/{test_timeframe} ---")

    # To run this test:
    # Ensure .env is configured (DATABASE_URL, optionally BINANCE_API_KEY)
    # From the project root: python -m backend.data_ingestion_service.historical_data_fetcher
    # Needs `PYTHONPATH=.` or similar for backend.app imports to work, or run from backend/
    # cd backend
    # python -m data_ingestion_service.historical_data_fetcher

    # asyncio.run(main_test()) # Uncomment to run test when module is executed directly
    pass 