# Remove temporary module-level print

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging
from typing import List
from sqlalchemy import select

# Add project root to sys.path if not already configured for routers
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) # Adjust based on actual file location
sys.path.insert(0, PROJECT_ROOT)

from .. import schemas, models
from ..database import SessionLocal, get_db

router = APIRouter(
    prefix="/news",
    tags=["News"]
)

# Configure logger for this specific module
logger = logging.getLogger(__name__) # __name__ will be 'backend.app.routers.news'
logger.setLevel(logging.DEBUG) # Force logger to output DEBUG and higher messages

# Optional: Add a handler if you suspect no handlers are configured for this logger
# (though Uvicorn usually sets up a basic console handler)
# if not logger.hasHandlers():
#     handler = logging.StreamHandler(sys.stdout)
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)

DEFAULT_NEWS_LIMIT = 15

@router.get("/{symbol}", response_model=List[schemas.NewsArticleRead])
async def get_news_for_symbol(
    symbol: str, 
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100) # Default 20, max 100
):
    """
    Retrieve the latest news articles for a given financial symbol.
    - **symbol**: The financial symbol (e.g., AAPL, BTCUSDT) to fetch news for.
    - **limit**: Maximum number of news articles to return.
    """
    print(f"<<<<< INSIDE get_news_for_symbol for {symbol} (router module: {__name__}) >>>>>") # Raw print for debugging
    logger.debug("This is a DEBUG message from get_news_for_symbol.") # Test DEBUG level
    logger.info(f"Received request for news for symbol: {symbol}, limit: {limit}") # Log request
    print(f"<<<<< 2 - INSIDE get_news_for_symbol for {symbol} (router module: {__name__}) >>>>>") # Raw print for debugging
    try:
        print(f"<<<<< 3 - INSIDE get_news_for_symbol for {symbol} (router module: {__name__}) >>>>>") # Raw print for debugging
        # Convert our internal symbols (like BTCUSDT) to the symbol stored in the DB 
        # if there's a mapping, otherwise use the provided symbol.
        # For now, we assume the news_fetcher_service stores news using our internal symbols.
        # So, direct query with 'symbol' should work.
        
        stmt = (
            select(models.NewsArticle)
            .filter(models.NewsArticle.symbol == symbol)
            .order_by(models.NewsArticle.published_at.desc())
            .limit(limit)
        )
        # For synchronous session, execute directly
        news_articles = db.execute(stmt).scalars().all()

        logger.info(f"Found {len(news_articles)} articles in DB for symbol: {symbol}") # Log count

        print(f"<<<<< 4 - INSIDE get_news_for_symbol for {symbol}:  Found {len(news_articles)} articles in DB for symbol: {symbol}")# Raw print for debugging

        if news_articles:
            print(f"<<<<< 5 - INSIDE get_news_for_symbol for {symbol}: found some articles")
            logger.debug(f"First few articles for {symbol}:")
            for i, article_db in enumerate(news_articles[:3]): # Log first 3 articles
                logger.debug(
                    f"  Article {i+1}: ID={article_db.external_article_id}, "
                    f"Headline='{article_db.headline}', "
                    f"Published='{article_db.published_at}', "
                    f"Snippet='{article_db.snippet[:100]}...', " # Log first 100 chars of snippet
                    f"Sentiment='{article_db.sentiment_score_external}'"
                )
                
        # Pydantic V2: .from_orm is deprecated, models are instantiated directly
        # response_articles = [NewsArticleRead.model_validate(article) for article in news_articles]
        # No, NewsArticleRead is the Pydantic model, NewsArticleDB is the ORM model.
        # We need to convert ORM models to Pydantic models if they are different.
        # Assuming NewsArticleRead can be created from NewsArticleDB instances
        
        if not news_articles:
            logger.info(f"No news found for symbol: {symbol}, returning empty list.")
            return [] # Explicitly return empty list
        
        # Manually construct NewsArticleRead to ensure correct field mapping if needed,
        # or rely on Pydantic's from_orm equivalent if NewsArticleRead is set up for it.
        # For now, let's assume direct compatibility or that Pydantic handles it.
        print(f"<<<<< 6 - INSIDE get_news_for_symbol for {symbol} (articles): {news_articles}")
        return news_articles # FastAPI will handle Pydantic model conversion if types match up
    except Exception as e:
        logger.error(f"Error fetching news for symbol {symbol} from DB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching news.") 