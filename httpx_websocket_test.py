import asyncio
import httpx
import logging

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_httpx_websocket():
    logger.info(f"Using httpx version: {httpx.__version__}")
    logger.info(f"httpx module loaded from: {httpx.__file__}")
    
    # A public WebSocket echo server
    # For wss (secure): wss://socketsbay.com/wss/v2/1/demo/
    # For ws (insecure, might be simpler for initial test if SSL issues are suspected, though current error is AttributeError):
    # ws://websockets.chilkat.io/wsChilkatEcho.ashx (seems to be down)
    # Using a known public echo server from a library like `websockets` documentation or examples is good.
    # Let's use a commonly cited one for testing: wss://echo.websocket.org (though this one seems to be an alias or might be deprecated)
    # A more reliable one: wss://www.piesocket.com/websocket-tester (requires a free API key usually)
    # Let's try one from `socketsbay` that is often used for demos:
    test_ws_url = "wss://socketsbay.com/wss/v2/1/demo/"

    logger.info(f"Attempting to connect to: {test_ws_url}")

    try:
        async with httpx.AsyncClient(timeout=30) as client: # Removed verify=False for now, as it's an AttributeError
            logger.info(f"AsyncClient created. Type: {type(client)}")
            logger.info(f"Attributes of client object: {dir(client)}")
            
            if hasattr(client, 'websocket_connect'):
                logger.info("Client object HAS 'websocket_connect' attribute.")
                async with client.websocket_connect(test_ws_url) as websocket:
                    logger.info(f"Successfully connected to {test_ws_url}")
                    await websocket.send_text("Hello, WebSocket!")
                    response = await websocket.receive_text()
                    logger.info(f"Received message: {response}")
                    await websocket.close()
                    logger.info("WebSocket closed.")
            else:
                logger.error("Client object DOES NOT HAVE 'websocket_connect' attribute.")
                # Explicitly try to access to trigger the error for confirmation
                _ = client.websocket_connect 

    except AttributeError as ae:
        logger.error(f"Caught AttributeError: {ae}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_httpx_websocket()) 