"""
@file: models.py
@description: SQLAlchemy models for the application.
@dependencies: sqlalchemy, pydantic (for enums if used)
@created: [v2] 2025-05-18
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLAlchemyEnum, func, BigInteger, Numeric, PrimaryKeyConstraint, Float, Index, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
import enum

Base = declarative_base()

class SubscriptionPlanEnum(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"

# Enum for Trade Direction
class TradeDirectionEnum(str, enum.Enum):
    LONG = "long"
    SHORT = "short"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    first_joined_at = Column(DateTime(timezone=True), server_default=func.now())
    subscription_plan = Column(SQLAlchemyEnum(SubscriptionPlanEnum, name="subscriptionplanenum", create_type=False), default=SubscriptionPlanEnum.FREE)
    start_of_subscription = Column(DateTime(timezone=True), nullable=True)
    end_of_subscription = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, nickname='{self.nickname}', email='{self.email}')>" 

class Kline(Base):
    __tablename__ = "klines"

    # Composite Primary Key
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), nullable=False, index=True)

    # Kline data fields
    open_price = Column(Numeric(precision=18, scale=8), nullable=False)
    high_price = Column(Numeric(precision=18, scale=8), nullable=False)
    low_price = Column(Numeric(precision=18, scale=8), nullable=False)
    close_price = Column(Numeric(precision=18, scale=8), nullable=False)
    volume = Column(Numeric(precision=24, scale=8), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=False)
    quote_asset_volume = Column(Numeric(precision=24, scale=8), nullable=False)
    number_of_trades = Column(BigInteger, nullable=False)
    taker_buy_base_asset_volume = Column(Numeric(precision=24, scale=8), nullable=False)
    taker_buy_quote_asset_volume = Column(Numeric(precision=24, scale=8), nullable=False)

    # Define the composite primary key constraint
    __table_args__ = (PrimaryKeyConstraint('symbol', 'timeframe', 'open_time', name='pk_klines'),
                      # Add any other table-level constraints here if needed in the future
                     )

    def __repr__(self):
        return f"<Kline(symbol='{self.symbol}', timeframe='{self.timeframe}', open_time='{self.open_time}')>" 

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    external_article_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    headline = Column(String, nullable=False)
    snippet = Column(String, nullable=True) # Changed from Text to String for consistency, can be Text if very long snippets are expected
    source_name = Column(String, nullable=False)
    article_url = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sentiment_score_external = Column(Float, nullable=True)
    sentiment_category_derived = Column(String, nullable=True) # "Positive", "Neutral", "Negative"
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_news_articles_symbol_published_at', "symbol", "published_at"),
    )

    def __repr__(self):
        return f"<NewsArticle(id={self.id}, symbol='{self.symbol}', headline='{self.headline[:50]}...')>" 

# New TradeNote model for Perflogs
class TradeNote(Base):
    __tablename__ = "tradenotes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_ticker = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)
    # Use explicit string values for PgEnum to match the database native enum
    trade_direction = Column(PgEnum('long', 'short', 
                                    name="tradedirectionenum", 
                                    create_type=False),
                           nullable=False)
    entry_price = Column(Numeric(precision=18, scale=8), nullable=False)
    exit_price = Column(Numeric(precision=18, scale=8), nullable=False)
    margin = Column(Numeric(precision=18, scale=2), nullable=False) # Assuming margin is a monetary value
    leverage = Column(Numeric(precision=5, scale=2), default=1.0, nullable=False)
    pnl = Column(Numeric(precision=18, scale=2), nullable=False) # Profit or Loss, monetary value
    note_text = Column(Text, nullable=True) # Max 1000 chars handled by app logic/validation, DB Text type is flexible
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_tradenotes_user_asset_created', "user_id", "asset_ticker", "created_at"),
    )

    def __repr__(self):
        return f"<TradeNote(id={self.id}, user_id={self.user_id}, asset_ticker='{self.asset_ticker}', direction='{self.trade_direction}')>" 