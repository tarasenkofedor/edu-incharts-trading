"""
@file: schemas.py
@description: Pydantic models (schemas) for API request/response validation and serialization.
@dependencies: pydantic, datetime, enum (from models)
@created: [v2] 2025-05-18
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from .models import SubscriptionPlanEnum, TradeDirectionEnum

# Base User properties
class UserBase(BaseModel):
    email: EmailStr
    nickname: str = Field(..., min_length=3, max_length=50)

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Properties to receive via API on update (all optional)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nickname: Optional[str] = Field(None, min_length=3, max_length=50)
    is_active: Optional[bool] = None
    subscription_plan: Optional[SubscriptionPlanEnum] = None
    start_of_subscription: Optional[datetime] = None
    end_of_subscription: Optional[datetime] = None

# Properties stored in DB (hashed password)
class UserInDBBase(UserBase):
    id: int
    is_active: bool = True
    first_joined_at: datetime
    subscription_plan: SubscriptionPlanEnum = SubscriptionPlanEnum.FREE
    start_of_subscription: Optional[datetime] = None
    end_of_subscription: Optional[datetime] = None

    class Config:
        from_attributes = True # Pydantic V2 way

# Additional properties to return via API
class User(UserInDBBase):
    pass

# Properties stored in DB including hashed password
class UserInDB(UserInDBBase):
    hashed_password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    nickname: Optional[str] = None

# --- Kline Schemas for API --- 
class KlineBase(BaseModel):
    symbol: str
    timeframe: str
    open_time: datetime # Expect datetime from ORM/internal processing
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    close_time: datetime # Expect datetime from ORM/internal processing
    quote_asset_volume: float
    number_of_trades: int
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float
    is_closed: Optional[bool] = None # Made optional, will be None if not from Binance source that provides it

class KlineRead(KlineBase):
    class Config:
        from_attributes = True
        # This will encode datetime to int (ms timestamp) for JSON output
        json_encoders = {
            datetime: lambda dt: int(dt.timestamp() * 1000)
        }

class KlineHistoricalResponse(BaseModel):
    klines: List[KlineRead]
    backfill_status: Optional[str] = None
    backfill_last_updated_ts: Optional[int] = None

class NewsArticleBase(BaseModel):
    external_article_id: str
    symbol: str
    headline: str
    snippet: Optional[str] = None
    source_name: str
    article_url: str
    image_url: Optional[str] = None
    published_at: datetime
    sentiment_score_external: Optional[float] = None
    sentiment_category_derived: Optional[str] = None
    fetched_at: datetime # Added for consistency with DB model if needed by frontend

    class Config:
        from_attributes = True # Replaces orm_mode = True

class NewsArticleRead(NewsArticleBase):
    id: int
    # Any additional fields for reading that differ from base can be added here
    # For now, it inherits all fields from NewsArticleBase and adds 'id'

# If you need a create schema (though articles are created by the service)
# class NewsArticleCreate(NewsArticleBase):
#     pass 

# --- TradeNote Schemas for Perflogs ---
class TradeNoteBase(BaseModel):
    asset_ticker: str = Field(..., max_length=20) # e.g., BTCUSDT
    timeframe: str = Field(..., max_length=10)    # e.g., 15m
    trade_direction: TradeDirectionEnum
    entry_price: Decimal = Field(..., gt=0)
    exit_price: Decimal = Field(..., gt=0)
    margin: Decimal = Field(..., gt=0)
    leverage: Decimal = Field(default=1.0, ge=1.0)
    pnl: Decimal # Can be negative
    note_text: Optional[str] = Field(None, max_length=1000)

    class Config:
        # This will allow pydantic to convert Decimal to float for JSON
        json_encoders = {
            Decimal: lambda d: float(d)
        }

class TradeNoteCreate(TradeNoteBase):
    # No additional fields needed for creation beyond TradeNoteBase
    # user_id will be sourced from the authenticated user in the endpoint
    pass

class TradeNoteRead(TradeNoteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        # Inherit and potentially extend json_encoders if needed,
        # or rely on TradeNoteBase's encoders if sufficient.
        # For now, TradeNoteBase's Decimal encoder should cover it.
        # If datetime needs special formatting for TradeNoteRead, add it here.
        # Example:
        # json_encoders = {
        #     **TradeNoteBase.Config.json_encoders, # Inherit from base
        #     datetime: lambda dt: dt.isoformat() # Or your preferred format
        # }
        # Using default Pydantic datetime serialization (ISO format string) for now.
        # If millisecond timestamps are preferred like in KlineRead:
        json_encoders = {
            Decimal: lambda d: float(d), # from TradeNoteBase logic
            datetime: lambda dt: int(dt.timestamp() * 1000)
        } 