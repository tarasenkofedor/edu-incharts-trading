import asyncio
# import httpx # Removed httpx
import websockets # Added websockets
import json
import logging
import time
# import sys # Keep for sys.path logging for now - REMOVING
# import inspect # Keep for inspect.getfile logging for now - REMOVING

from backend.app.config import settings # Assuming settings has BINANCE_WS_BASE_URL

logger = logging.getLogger(__name__)

# Default backoff parameters
INITIAL_RECONNECT_DELAY_SECONDS = 5
MAX_RECONNECT_DELAY_SECONDS = 60
BACKOFF_FACTOR = 2

class BinanceWebSocketManager:
    def __init__(self, symbol: str, timeframe: str, data_handler_callback, shutdown_event_global):
        self.symbol = symbol.lower() # Binance uses lowercase symbols in stream names
        self.timeframe = timeframe
        self.data_handler_callback = data_handler_callback
        self.settings = settings
        self.ws_url = self._get_websocket_url()
        
        self._reconnect_attempts = 0
        self._current_delay = INITIAL_RECONNECT_DELAY_SECONDS
        self._websocket_connection = None # Renamed for clarity with websockets library
        self.shutdown_event = shutdown_event_global
        self.is_running = False

    def _get_websocket_url(self) -> str:
        """Constructs the Binance WebSocket stream URL."""
        # Example: wss://stream.binance.com:9443/ws/btcusdt@kline_1m
        # Using default Binance spot WebSocket URL. If PRO/testnet needed, this should be configurable.
        base_url = getattr(self.settings, 'BINANCE_WS_BASE_URL', "wss://stream.binance.com:9443/ws")
        stream_name = f"{self.symbol}@kline_{self.timeframe}"
        url = f"{base_url}/{stream_name}"
        logger.debug(f"Constructed WebSocket URL for {self.symbol}/{self.timeframe}: {url}")
        return url

    def _parse_kline_message(self, message_str: str):
        """
        Parses the incoming JSON message from Binance.
        Returns a structured kline dictionary if it's a valid kline event, otherwise None.
        The 'is_closed' status is included in the returned dictionary.
        """
        try:
            data = json.loads(message_str)
            if data.get('e') == 'kline':
                kline_data = data.get('k')
                if kline_data: # Check if kline data ('k') exists
                    parsed_kline = {
                        'event_type': data.get('e'),
                        'event_time': data.get('E'),
                        'symbol': kline_data.get('s'),
                        'timeframe': kline_data.get('i'),
                        'open_time': kline_data.get('t'),
                        'open': kline_data.get('o'),
                        'high': kline_data.get('h'),
                        'low': kline_data.get('l'),
                        'close': kline_data.get('c'),
                        'volume': kline_data.get('v'),
                        'close_time': kline_data.get('T'),
                        'quote_asset_volume': kline_data.get('q'),
                        'number_of_trades': kline_data.get('n'),
                        'is_closed': kline_data.get('x', False), # Default to False if 'x' is not present
                        'taker_buy_base_asset_volume': kline_data.get('V'),
                        'taker_buy_quote_asset_volume': kline_data.get('Q')
                    }
                    # Basic validation: ensure essential fields for any kline update are present
                    if not all([parsed_kline['symbol'], parsed_kline['timeframe'], parsed_kline['open_time'], parsed_kline['close']]):
                        logger.warning(f"[{self.symbol.upper()}/{self.timeframe}] Kline message missing essential fields: {kline_data}")
                        return None
                    
                    # Log whether it's a final or non-final update
                    if parsed_kline['is_closed']:
                        logger.debug(f"[{self.symbol.upper()}/{self.timeframe}] Received final (closed) kline update: OT {parsed_kline['open_time']}")
                    else:
                        logger.debug(f"[{self.symbol.upper()}/{self.timeframe}] Received non-final (tick) kline update: OT {parsed_kline['open_time']}, C {parsed_kline['close']}")
                    return parsed_kline
                else:
                    logger.warning(f"[{self.symbol.upper()}/{self.timeframe}] 'kline' event received but 'k' data is missing or empty: {data}")
                    return None
            elif 'error' in data:
                 logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Received error message from WebSocket: {data}")
                 return None
            else:
                # Other message types (e.g., subscription confirmation), log if unexpected
                logger.debug(f"[{self.symbol.upper()}/{self.timeframe}] Received non-kline message: {data.get('e', data)}")
                return None
        except json.JSONDecodeError:
            logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Failed to decode JSON message: {message_str}")
            return None
        except Exception as e:
            logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Error parsing message: {e}. Message: {message_str}", exc_info=True)
            return None

    async def run(self):
        # print(f"SYNC_PRINT: [{self.symbol.upper()}/{self.timeframe}] BinanceWebSocketManager.run() entered.", flush=True) # DIAGNOSTIC PRINT - REMOVED
        """Main connection and message handling loop."""
        # logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Python sys.path: {sys.path}") # REMOVED
        # logger.info(f"[{self.symbol.upper()}/{self.timeframe}] httpx module loaded from: {httpx.__file__}") # REMOVED
        # logger.info(f"[{self.symbol.upper()}/{self.timeframe}] httpx version used: {httpx.__version__}") # REMOVED

        self.is_running = True
        logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Starting WebSocket manager (using websockets library).")

        connected_successfully_flag = False

        while not self.shutdown_event.is_set() and self.is_running:
            connected_successfully_flag = False
            try:
                logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Attempting to connect to {self.ws_url} (Attempt: {self._reconnect_attempts + 1})")
                # websockets.connect() parameters:
                # - ping_interval: Sends a PING frame every N seconds and waits for PONG.
                # - ping_timeout: Timeout for PONG response. If None, PONGs are not checked.
                # - close_timeout: Timeout for closing handshake.
                # - ssl: Can pass an SSLContext for custom SSL configuration. Default handles wss.
                # - extra_headers: For custom headers, if needed.
                # Using a default ping_interval of 20s as recommended by websockets library for keeping NAT open
                # Binance might also have its own keepalive recommendations (e.g. application level pings)
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20, # Standard keepalive ping from websockets library
                    ping_timeout=20
                ) as websocket_conn:
                    self._websocket_connection = websocket_conn
                    self._reconnect_attempts = 0
                    self._current_delay = INITIAL_RECONNECT_DELAY_SECONDS
                    connected_successfully_flag = True
                    logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Successfully connected to {self.ws_url}. Listening for messages...")

                    while not self.shutdown_event.is_set() and self.is_running:
                        try:
                            # Ensure connection is open before attempting to receive
                            if not websocket_conn: # Should not happen if async with block is active
                                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Critical: websocket_conn is None in receive loop.")
                                connected_successfully_flag = False
                                break
                            
                            # websocket_conn.ensure_open() # REMOVED - Rely on recv() to raise ConnectionClosed

                            message_str = await websocket_conn.recv()
                            # logger.debug(f"[{self.symbol.upper()}/{self.timeframe}] Received raw message: {message_str}")
                            
                            # Parse the message before calling the data handler
                            parsed_message = self._parse_kline_message(message_str)
                            
                            if parsed_message: # Ensure message is valid and parsed
                                # The data_handler_callback is functools.partial(kline_data_processor, ...)
                                # kline_data_processor's first argument 'kline_data' will receive parsed_message.
                                asyncio.create_task(self.data_handler_callback(parsed_message))
                            # If parsed_message is None, it's logged by _parse_kline_message, so no further action here.
                            
                        except websockets.exceptions.ConnectionClosedOK:
                            logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket connection closed gracefully (OK).")
                            connected_successfully_flag = False # Ensure we attempt reconnect if not shutting down
                            break # Break inner loop
                        except websockets.exceptions.ConnectionClosedError as cce:
                            logger.warning(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket connection closed with error: {cce}. Code: {cce.code}, Reason: {cce.reason}. Attempting to reconnect.")
                            connected_successfully_flag = False
                            break # Break inner loop
                        except websockets.exceptions.ConnectionClosed as cc_general: # Catch any other ConnectionClosed from ensure_open
                            logger.warning(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket connection found closed by ensure_open() or recv(): {cc_general}.")
                            connected_successfully_flag = False
                            break # Break inner loop
                        except asyncio.CancelledError:
                            logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Main receive loop's task cancelled.")
                            connected_successfully_flag = False # Treat as disconnect for potential reconnect
                            raise # Re-raise to be handled by the outer task structure if needed
                        except Exception as e:
                            logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Error during message processing: {e}", exc_info=True)
                            # Decide if this error should also trigger a reconnect
                            # For now, assuming it might be a transient message error.
                    if not connected_successfully_flag:
                        # This log might be redundant if a specific error was already logged above
                        # logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Connection attempt {self._reconnect_attempts + 1} did not establish connection or failed post-connection. Check logs.")
                        self._reconnect_attempts += 1
                        logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Will attempt reconnection in {self._current_delay} seconds... (Next attempt: {self._reconnect_attempts + 1})")
                        await asyncio.sleep(self._current_delay)
                        self._current_delay = min(self._current_delay * BACKOFF_FACTOR, MAX_RECONNECT_DELAY_SECONDS)
                    else:
                        # If we successfully connected and then disconnected (e.g., ConnectionClosedOK or ConnectionClosedError)
                        logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket disconnected. Attempting immediate reconnect (unless shutting down).")
                        self._reconnect_attempts = 0
                        self._current_delay = INITIAL_RECONNECT_DELAY_SECONDS
            except websockets.exceptions.InvalidURI as iuri:
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Invalid WebSocket URI: {self.ws_url}. Error: {iuri}", exc_info=True)
                self.is_running = False # Critical error, stop the manager
                break
            except websockets.exceptions.WebSocketException as wse:
                 logger.error(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket connection/protocol error: {wse}", exc_info=True)
                 # This will be caught by the generic backoff logic below
            except ConnectionRefusedError:
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Connection refused for {self.ws_url}.", exc_info=True)
            except asyncio.TimeoutError: # Should be less common with ping_interval/timeout in connect
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Connection attempt timed out for {self.ws_url}.", exc_info=True)
            except OSError as ose: # Catch network-related OS errors (e.g., Host Down, Network Unreachable)
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Network OSError during connection: {ose}", exc_info=True)
            except Exception as e:
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] General exception in connection loop: {e}", exc_info=True)

            if not self.shutdown_event.is_set() and self.is_running:
                if not connected_successfully_flag:
                    # This log might be redundant if a specific error was already logged above
                    # logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Connection attempt {self._reconnect_attempts + 1} did not establish connection or failed post-connection. Check logs.")
                    self._reconnect_attempts += 1
                    logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Will attempt reconnection in {self._current_delay} seconds... (Next attempt: {self._reconnect_attempts + 1})")
                    await asyncio.sleep(self._current_delay)
                    self._current_delay = min(self._current_delay * BACKOFF_FACTOR, MAX_RECONNECT_DELAY_SECONDS)
                else:
                    # If we successfully connected and then disconnected (e.g., ConnectionClosedOK or ConnectionClosedError)
                    logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket disconnected. Attempting immediate reconnect (unless shutting down).")
                    self._reconnect_attempts = 0
                    self._current_delay = INITIAL_RECONNECT_DELAY_SECONDS
            else:
                logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Shutdown initiated or no longer running, stopping reconnections.")
                break

        self.is_running = False
        if self._websocket_connection: # Simplified check
            logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Ensuring WebSocket connection is closed before exiting run loop.")
            try:
                await self._websocket_connection.close()
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Connection already closed when ensuring closure in run loop.")
            except Exception as e:
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Error during explicit close in run loop: {e}", exc_info=True)

        logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket manager stopped.")

    async def stop(self):
        """Stops the WebSocket manager gracefully."""
        logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Stop called for WebSocket manager.")
        self.is_running = False # Signal the run loop to exit
        # self.shutdown_event.set() # This is a global event, should be set by the main service controller
        
        if self._websocket_connection: # Simplified check
            try:
                logger.info(f"[{self.symbol.upper()}/{self.timeframe}] Attempting to close WebSocket connection during stop.")
                await self._websocket_connection.close() 
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket already closed while trying to stop.")
            except Exception as e:
                logger.error(f"[{self.symbol.upper()}/{self.timeframe}] Error closing WebSocket during stop: {e}", exc_info=True)
        else:
            logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket connection was not open or not established when stop was called.")
        logger.info(f"[{self.symbol.upper()}/{self.timeframe}] WebSocket manager has been signaled to stop and attempted cleanup.")

# Example Usage (for testing purposes, normally used by main.py in data_ingestion_service)
async def dummy_data_handler(kline_data):
    logger.info(f"[DUMMY_HANDLER] Received kline: {kline_data['symbol']}@{kline_data['timeframe']} - Close: {kline_data['close']} @ {kline_data['close_time']}")

async def main_test():
    # setup_logging is expected to be imported if this test is run
    # from backend.data_ingestion_service.service_utils import setup_logging 
    # setup_logging(level=logging.DEBUG)
    global_shutdown = asyncio.Event()
    
    # Test with one symbol/timeframe
    # BTCUSDT 1 minute
    manager1 = BinanceWebSocketManager(symbol="BTCUSDT", timeframe="1m", data_handler_callback=dummy_data_handler, shutdown_event_global=global_shutdown)
    
    # ETHUSDT 1 minute
    # manager2 = BinanceWebSocketManager(symbol="ETHUSDT", timeframe="1m", data_handler_callback=dummy_data_handler, shutdown_event_global=global_shutdown)

    tasks = [asyncio.create_task(manager1.run())]
    # tasks.append(asyncio.create_task(manager2.run()))

    try:
        await asyncio.gather(*tasks) # This will run until all managers complete or are cancelled
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received in main_test. Signaling shutdown.")
        global_shutdown.set()
        for manager in [manager1]: #, manager2]:
            await manager.stop() # Ensure stop is called
        # Wait for tasks to actually finish after stop is called and shutdown_event is set
        # Setting a timeout for gather to prevent hanging if tasks don't respect cancellation/shutdown promptly
        done, pending = await asyncio.wait(tasks, timeout=10.0)
        for task in pending:
            logger.warning(f"Task {task.get_name()} did not complete during shutdown, cancelling.")
            task.cancel()
            try:
                await task # Allow task to process cancellation
            except asyncio.CancelledError:
                logger.info(f"Task {task.get_name()} cancelled successfully.")
            except Exception as e:
                logger.error(f"Exception in task {task.get_name()} during final cancellation: {e}")
    finally:
        logger.info("Main_test finished.")

if __name__ == "__main__":
    # To run this test: python -m backend.data_ingestion_service.binance_connector
    # Ensure your PYTHONPATH is set correctly if running from project root, e.g.:
    # export PYTHONPATH=$(pwd)
    # python backend/data_ingestion_service/binance_connector.py
    from backend.data_ingestion_service.service_utils import setup_logging # Relative import for testing
    asyncio.run(main_test()) 