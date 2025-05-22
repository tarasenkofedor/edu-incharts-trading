import uvicorn
from app.main import app # Import the FastAPI app instance directly

if __name__ == "__main__":
    uvicorn.run(
        app,  # Pass the app instance directly
        host="0.0.0.0",
        port=8000,
        # reload=True, # Cannot be used when passing app instance directly
        ws="websockets",  # Explicitly use the websockets library
        ws_max_size=16777216,  # Default from Uvicorn CLI
        loop="asyncio",      # Explicitly set the event loop
        lifespan="on",     # Explicitly handle lifespan events
        # The critical part for WebSockets and origin:
        # We are relying on Starlette's default behavior for WebSockets,
        # which should be more permissive with origins if no specific
        # 'ws_handlers' or other strict Uvicorn policies are blocking it.
        # By *not* specifying a restrictive ws_handler here, and having
        # addressed CORSMiddleware for HTTP, we test if the default is open enough.
        # If this still fails, the issue is deeply rooted in a default Uvicorn/Starlette
        # security policy that isn't being overridden by standard configurations.
        #
        # Forcing a specific ws_handler that allows all origins:
        # This is a more direct way to tell Uvicorn how to handle WS.
        # We will use a basic handler that just passes it to the app.
        # Starlette's WebSocketResponse (used by FastAPI) should then
        # handle the origin based on its own logic (which is typically permissive
        # unless a middleware further restricts it).
        #
        # Uvicorn doesn't have a direct 'allow all origins for websockets' via this run command.
        # The 'app.main:app' should handle it if Uvicorn itself doesn't block it first.
        # Our FastAPI app *should* be reached if Uvicorn doesn't prematurely kill the connection.
        #
        # Let's ensure our CORSMiddleware in main.py is broad, and then this
        # programmatic run without overly strict Uvicorn WS policies might work.
        # The key is to see if our FastAPI endpoint LOGS are hit.
    ) 