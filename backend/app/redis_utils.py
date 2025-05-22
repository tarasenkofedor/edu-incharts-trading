import redis
from .config import settings

def get_redis_connection():
    """
    Establishes a connection to Redis using settings from the config.
    Returns a Redis client instance.
    """
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,  # Default Redis DB
            decode_responses=True  # Decode responses from bytes to strings
        )
        r.ping()  # Verify connection
        print(f"Successfully connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return r
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        # Depending on how critical Redis is at startup, you might want to:
        # 1. Raise the exception: raise
        # 2. Return None and let the caller handle it: return None
        # 3. Exit the application: sys.exit("Failed to connect to Redis.")
        # For now, we'll print the error and return None.
        return None

def ping_redis(redis_client: redis.Redis):
    """
    Pings the Redis server to check the connection.
    Returns True if successful, False otherwise.
    """
    if not redis_client:
        print("Redis client is not available.")
        return False
    try:
        return redis_client.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"Redis ping failed: {e}")
        return False

# Example of how to get a connection (optional, can be called from elsewhere)
# redis_client = get_redis_connection()

# if redis_client:
#     print(f"Ping successful: {ping_redis(redis_client)}") 