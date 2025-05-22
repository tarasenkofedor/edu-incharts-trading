"""
@file: config.py
@description: Configuration settings for the application, loaded from .env file.
@dependencies: pydantic-settings
@created: [v2] 2025-05-18
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator # Import Field for default values if needed, and field_validator
import os
from typing import Optional, List

# Determine the project root directory (assuming config.py is in backend/app/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) 
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str # Should be mandatory
    ALGORITHM: str = "HS256" # Default algorithm if not in .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Default to 30 minutes
    # ANONYMOUS_TOKEN_EXPIRE_MINUTES: Optional[int] = 10080 # This was in your .env example, decide if needed

    MARKETAUX_API_TOKEN: str # Added for News Fetcher Service
    NEWSDATA_IO_API_TOKEN: str # Added for News Fetcher Service
    COINDESK_API_TOKEN: str # Added for CoinDesk News

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Binance API Credentials (Optional, for historical backfill)
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None

    # Proactively Tracked Symbols & Timeframes for Live Data Ingestion
    PROACTIVE_SYMBOLS: str = ""
    PROACTIVE_TIMEFRAMES: str = ""
    PROACTIVE_TIMEFRAMES_LIST: List[str] = Field(default_factory=list)

    # Max number of klines to store in Redis sorted set per symbol/timeframe
    MAX_KLINES_IN_REDIS: int = 2000 # Approx 1.4 days for 1m klines

    # Historical Data Backfill Configuration
    INITIAL_BACKFILL_DAYS: int = 14 # Days to backfill if no data exists for a symbol/timeframe
    HISTORICAL_FETCH_BUFFER_KLINES: int = 1 # Number of klines "ago" from current time to target for backfilling

    # API Data Retrieval Configuration
    API_REDIS_LOOKBACK_MS: int = 5 * 60 * 1000 # 5 minutes in milliseconds, how far back to check Redis in API endpoint

    # WebSocket Configuration
    WEBSOCKET_PING_INTERVAL_SECONDS: int = 30 # Interval in seconds for sending pings to WebSocket clients

    # News Fetcher Configuration
    USE_VADER_SENTIMENT_ANALYSIS: bool = True # If True, use VADER. If False, use API-provided sentiment (if available).

    @field_validator("PROACTIVE_TIMEFRAMES_LIST", mode="before")
    @classmethod
    def populate_proactive_timeframes_list(cls, v, values):
        # This validator relies on PROACTIVE_TIMEFRAMES being processed already.
        # Pydantic v2 processes fields in order, so this should be fine.
        # If PROACTIVE_TIMEFRAMES is not yet in `values.data` (e.g. if this validator runs first)
        # we might need to adjust or use a root_validator.
        # For now, let's assume PROACTIVE_TIMEFRAMES is available.
        proactive_timeframes_str = values.data.get("PROACTIVE_TIMEFRAMES", "")
        if proactive_timeframes_str:
            return [tf.strip() for tf in proactive_timeframes_str.split(',') if tf.strip()]
        return []

    class Config:
        env_file = ENV_FILE_PATH 
        env_file_encoding = "utf-8"
        extra = 'ignore' # Ignore extra fields from .env if they are not in Settings model

settings = Settings() 