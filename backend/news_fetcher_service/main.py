import asyncio
import logging
import os
import sys
import datetime # Added for timestamp conversion
# from decimal import Decimal # Not used directly in the current logic with CoinDesk sentiment

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer # VADER import

# Add project root to sys.path to allow absolute imports
# Assuming this script is in backend/news_fetcher_service/ and models are in backend/app/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models import NewsArticle
from backend.app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize VADER Sentiment Analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

# NewsData.io for Stocks
NEWSDATA_IO_API_TOKEN = settings.NEWSDATA_IO_API_TOKEN
NEWSDATA_IO_BASE_URL = "https://newsdata.io/api/1"

# CoinDesk for Crypto
COINDESK_API_TOKEN = settings.COINDESK_API_TOKEN
COINDESK_BASE_URL = "https://data-api.coindesk.com"

STOCK_SYMBOLS_TO_TRACK = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA"]
CRYPTO_SYMBOLS_TO_TRACK_INTERNAL = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Mapping internal crypto symbols to what CoinDesk might use in CATEGORY_DATA (case-insensitive check)
CRYPTO_CATEGORY_MAP_COINDESK = {
    "BTCUSDT": "btc",
    "ETHUSDT": "eth", # Check CoinDesk's actual category for Ethereum
    "SOLUSDT": "sol"  # Based on coindesk_api_response_example.txt, category seems to be the ticker
}

# Fetch interval: 1 call every 6 minutes = 360 seconds
# Stock news (NewsData.io): 6 calls per cycle.
# Crypto news (CoinDesk): 1 call per cycle.
# Total 7 calls per cycle.
# NewsData.io free tier: 200 requests/day. 24h * 60m / 6m_interval = 240 cycles/day.
# 240 cycles * 6 stock_calls/cycle = 1440 NewsData.io calls/day. This is too high for NewsData.io free tier.
# We need to adjust NewsData.io fetching.
# Let's keep CoinDesk at 6 mins.
# For NewsData.io (stocks), if we fetch every hour (like before): 24 cycles * 6 calls = 144 calls/day. This is fine.
# So, crypto fetch cycle will be 6 mins. Stock fetch cycle will be 1 hour.
# This means the main loop needs to accommodate different schedules.

# For simplicity in this iteration, let's make the main loop run every 6 minutes.
# Stock fetching will happen less frequently within that loop.
GLOBAL_FETCH_INTERVAL_SECONDS = 5 * 60  # 5 minutes for the main loop (primarily for CoinDesk)
STOCK_FETCH_COUNTER_LIMIT = 10 # Fetch stocks every 10 * 6 minutes = 1 hour
stock_fetch_counter = 0

NEWSDATA_FETCH_LIMIT_PER_REQUEST = 10 # NewsData.io free tier limit per request
COINDESK_FETCH_LIMIT_PER_REQUEST = 50 # CoinDesk default and max is 50


async def fetch_stock_news(symbol: str):
    """Fetches news for a single stock symbol from NewsData.io /latest endpoint."""
    articles_data = []
    url = f"{NEWSDATA_IO_BASE_URL}/latest"
    params = {
        "apikey": NEWSDATA_IO_API_TOKEN,
        "q": symbol,
        "language": "en",
        "size": NEWSDATA_FETCH_LIMIT_PER_REQUEST,
    }
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching stock news for {symbol} from NewsData.io...")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            raw_articles = data.get("results", [])
            logger.info(f"Received {len(raw_articles)} raw articles for stock {symbol} from NewsData.io.")

            for article in raw_articles:
                headline = article.get("title", "")
                snippet = article.get("description", "")
                text_for_sentiment = f"{headline}. {snippet}"
                
                vader_score = None
                derived_category = "Neutral" # Default

                if settings.USE_VADER_SENTIMENT_ANALYSIS and text_for_sentiment.strip() and text_for_sentiment.strip() != '.':
                    try:
                        vs = sentiment_analyzer.polarity_scores(text_for_sentiment)
                        vader_score = vs['compound']
                        derived_category = map_sentiment_score_to_category(vader_score)
                        logger.debug(f"VADER for NewsData {article.get('article_id')}: Score {vader_score}, Cat: {derived_category}")
                    except Exception as e:
                        logger.error(f"Error during VADER sentiment analysis for NewsData article {article.get('article_id')}: {e}")
                        # Keep default Neutral category and None score on VADER error
                
                articles_data.append({
                    "external_article_id": article.get("article_id"),
                    "symbol": symbol,
                    "headline": headline,
                    "snippet": snippet,
                    "source_name": article.get("source_id"),
                    "article_url": article.get("link"),
                    "image_url": article.get("image_url"),
                    "published_at": article.get("pubDate"), # NewsData.io pubDate is usually a string, needs conversion in DB or here if not already
                    "sentiment_score_external": vader_score, # Store VADER compound score
                    "sentiment_category_derived": derived_category
                })
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching stock news for {symbol}: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching stock news for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching stock news for {symbol}: {e}")
    return articles_data

async def fetch_coindesk_crypto_news(internal_symbols_to_map: list[str]):
    """Fetches general crypto news from CoinDesk and maps to internal symbols based on categories."""
    articles_to_save = []
    url = f"{COINDESK_BASE_URL}/news/v1/article/list"
    headers = {
        "x-api-key": COINDESK_API_TOKEN
    }
    params = {
        "limit": COINDESK_FETCH_LIMIT_PER_REQUEST,
        "lang": "EN", # Explicitly set language
        "offset": 0 
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching crypto news from CoinDesk with params: {params}...")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            try:
                data = response.json()
                logger.info(f"CoinDesk Full Response JSON: {data}") # Log the full JSON response
            except Exception as json_e:
                logger.error(f"Error decoding CoinDesk JSON response: {json_e}")
                logger.error(f"CoinDesk Raw Response Text: {response.text}")
                return [] # Cannot proceed without valid JSON

            raw_articles = data.get("Data", []) # CoinDesk uses "Data" (capital D)
            if not isinstance(raw_articles, list): # Ensure it's a list
                logger.error(f"CoinDesk 'Data' field is not a list: {raw_articles}")
                raw_articles = []
                
            logger.info(f"Received {len(raw_articles)} raw articles from CoinDesk.")
            
            if data.get("Err") and data.get("Err") != {}:
                 logger.error(f"CoinDesk API returned an error in the 'Err' field: {data.get('Err')}")


            # Reverse map for quick lookup: "btc" -> "BTCUSDT"
            category_to_internal_symbol_map = {v.lower(): k for k, v in CRYPTO_CATEGORY_MAP_COINDESK.items()}

            for article in raw_articles:
                article_id = article.get("ID")
                title = article.get("TITLE")
                article_url = article.get("URL")
                published_on_ts = article.get("PUBLISHED_ON") # This is a Unix timestamp
                
                published_at_dt = None
                if published_on_ts:
                    try:
                        # Convert Unix timestamp to UTC datetime object
                        published_at_dt = datetime.datetime.fromtimestamp(int(published_on_ts), tz=datetime.timezone.utc)
                    except (ValueError, TypeError) as ts_e:
                        logger.warning(f"Could not convert timestamp '{published_on_ts}' for article ID {article_id}: {ts_e}")
                        continue # Skip article if timestamp is invalid

                source_name = article.get("SOURCE_DATA", {}).get("NAME")
                
                if not all([article_id, title, article_url, published_at_dt, source_name]): # Check published_at_dt
                    logger.warning(f"CoinDesk article ID {article_id} (Title: {title}) missing critical fields or invalid timestamp. Skipping.")
                    continue

                # Determine sentiment
                vader_score = None
                api_sentiment_category = article.get("SENTIMENT", "NEUTRAL").capitalize()
                if api_sentiment_category not in ["Positive", "Negative", "Neutral"]:
                    api_sentiment_category = "Neutral"
                
                derived_category = api_sentiment_category # Default to API sentiment

                if settings.USE_VADER_SENTIMENT_ANALYSIS:
                    body_snippet = article.get("BODY", "")[:500] # Use snippet for VADER
                    text_for_sentiment = f"{title}. {body_snippet}"
                    if text_for_sentiment.strip() and text_for_sentiment.strip() != '.':
                        try:
                            vs = sentiment_analyzer.polarity_scores(text_for_sentiment)
                            vader_score = vs['compound']
                            derived_category = map_sentiment_score_to_category(vader_score) # VADER overrides API if successful
                            logger.debug(f"VADER for CoinDesk {article_id}: Score {vader_score}, Cat: {derived_category}. (API was: {api_sentiment_category})")
                        except Exception as e:
                            logger.error(f"Error during VADER sentiment analysis for CoinDesk article {article_id}: {e}. Falling back to API sentiment: {api_sentiment_category}")
                            # On VADER error, derived_category remains api_sentiment_category
                    else:
                        logger.debug(f"Not enough text for VADER on CoinDesk article {article_id}. Using API sentiment: {api_sentiment_category}")
                        # derived_category remains api_sentiment_category
                else:
                    logger.debug(f"VADER disabled. Using CoinDesk API sentiment for {article_id}: {api_sentiment_category}")
                    # derived_category is already api_sentiment_category

                snippet_to_store = article.get("BODY", "")[:500]
                image_url = article.get("IMAGE_URL")

                matched_internal_symbols = set()
                categories_data = article.get("CATEGORY_DATA", [])
                if isinstance(categories_data, list):
                    for cat_obj in categories_data: 
                        cat_slug = cat_obj.get("CATEGORY", "").lower() # Use "CATEGORY" field, not "SLUG"
                        if cat_slug in category_to_internal_symbol_map:
                            matched_internal_symbols.add(category_to_internal_symbol_map[cat_slug])
                
                if not matched_internal_symbols:
                    logger.debug(f"CoinDesk article {article_id} did not match any tracked crypto categories. Categories from article: {[c.get('CATEGORY') for c in categories_data if c.get('CATEGORY')]}")
                    continue

                for internal_symbol in matched_internal_symbols:
                    articles_to_save.append({
                        "external_article_id": f"coindesk_{article_id}", 
                        "symbol": internal_symbol,
                        "headline": title,
                        "snippet": snippet_to_store,
                        "source_name": source_name,
                        "article_url": article_url,
                        "image_url": image_url,
                        "published_at": published_at_dt, 
                        "sentiment_score_external": vader_score, # Store VADER compound score (or None if not used/failed)
                        "sentiment_category_derived": derived_category
                    })
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching CoinDesk crypto news: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching CoinDesk crypto news: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching CoinDesk crypto news: {e}", exc_info=True)
    return articles_to_save

def map_sentiment_score_to_category(score: float | None) -> str:
    if score is None:
        return "Neutral"  # Default to Neutral if no score is available
    if score > 0.1:
        return "Positive"
    elif score < -0.1:
        return "Negative"
    else:
        return "Neutral"

async def save_articles_to_db(articles_data: list):
    if not articles_data:
        return 0

    db = SessionLocal()
    saved_count = 0
    try:
        for article_proc_data in articles_data:
            if not article_proc_data.get("external_article_id") or not article_proc_data.get("headline") or not article_proc_data.get("article_url") or not article_proc_data.get("published_at") or not article_proc_data.get("source_name") or not article_proc_data.get("symbol") : # Added symbol check
                logger.warning(f"Skipping article due to missing critical fields: {article_proc_data.get('headline')} for symbol {article_proc_data.get('symbol')}")
                continue

            stmt = pg_insert(NewsArticle).values(
                external_article_id=article_proc_data["external_article_id"],
                symbol=article_proc_data["symbol"],
                headline=article_proc_data["headline"],
                snippet=article_proc_data.get("snippet"),
                source_name=article_proc_data["source_name"],
                article_url=article_proc_data["article_url"],
                image_url=article_proc_data.get("image_url"),
                published_at=article_proc_data["published_at"],
                sentiment_score_external=article_proc_data.get("sentiment_score_external"),
                sentiment_category_derived=article_proc_data.get("sentiment_category_derived")
            ).on_conflict_do_nothing(
                index_elements=['external_article_id']
            )
            result = db.execute(stmt)
            if result.rowcount > 0:
                 saved_count += 1
        db.commit()
        logger.info(f"Saved {saved_count} new articles to DB out of {len(articles_data)} processed.")
    except SQLAlchemyError as e:
        logger.error(f"Database error saving articles: {e}")
        db.rollback()
    except Exception as e:
        logger.error(f"Unexpected error saving articles: {e}")
        db.rollback()
    finally:
        db.close()
    return saved_count

async def main_loop():
    global stock_fetch_counter
    logger.info("News Fetcher Service starting...")
    while True:
        logger.info(f"Main news fetching cycle. Interval: {GLOBAL_FETCH_INTERVAL_SECONDS}s.")
        all_fetched_articles = []

        # Fetch news for stock symbols (NewsData.io) - less frequently
        # if stock_fetch_counter % STOCK_FETCH_COUNTER_LIMIT == 0:
        #     logger.info("Executing scheduled stock news fetch (NewsData.io)...")
        #     for symbol in STOCK_SYMBOLS_TO_TRACK:
        #         await asyncio.sleep(1) # Stagger NewsData.io calls
        #         articles = await fetch_stock_news(symbol)
        #         if articles:
        #             all_fetched_articles.extend(articles)
        #     stock_fetch_counter = 0 # Reset counter
        
        # stock_fetch_counter += 1

        # Fetch crypto news (CoinDesk) - every cycle
        if CRYPTO_SYMBOLS_TO_TRACK_INTERNAL:
            logger.info("Executing crypto news fetch (CoinDesk)...")
            # await asyncio.sleep(1) # Optional delay, Coindesk is 1 call
            crypto_articles = await fetch_coindesk_crypto_news(CRYPTO_SYMBOLS_TO_TRACK_INTERNAL)
            if crypto_articles:
                all_fetched_articles.extend(crypto_articles)
        
        if all_fetched_articles:
            await save_articles_to_db(all_fetched_articles)
        else:
            logger.info("No new articles fetched in this cycle.")
        
        logger.info(f"Main news fetching cycle complete. Sleeping for {GLOBAL_FETCH_INTERVAL_SECONDS} seconds.")
        await asyncio.sleep(GLOBAL_FETCH_INTERVAL_SECONDS)

if __name__ == "__main__":
    # This allows running the service directly, e.g., python -m backend.news_fetcher_service.main
    if not NEWSDATA_IO_API_TOKEN:
        logger.error("NEWSDATA_IO_API_TOKEN not found in environment settings. Exiting.")
        sys.exit(1)
    if not COINDESK_API_TOKEN:
        logger.error("COINDESK_API_TOKEN not found in environment settings. Exiting.")
        sys.exit(1)
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("News Fetcher Service shutting down...")
    finally:
        logger.info("News Fetcher Service stopped.") 