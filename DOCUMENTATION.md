# InChart Project Documentation

**Version:** 0.0.7 (as of 2025-05-22)
**Author:** Fyodor Tarasenka (GitHub: tarasenkofedor)
**GitHub Repository:** [Placeholder for InChart GitHub Repository URL]

## 1. Introduction

This document provides a comprehensive overview of the InChart project's architecture, key technical decisions, and operational guidelines. It is intended to serve as a central reference for current and future development, complementing `TASKS.md`, `DIARY.md`, and `TECH_STACK.md`.

The primary goal of InChart is to develop a trading analysis platform, starting with an MVP that allows users to view financial charts, upload their own OHLCV and signal data, integrate live data from exchanges like Binance, view relevant news, and track their trading performance.

A critical constraint for the frontend development is the mandated use of a local, "raw" version of the `trading-vue-js` library, prohibiting its installation from external package managers like npm.

## 2. Core Technologies

A brief overview (refer to `TECH_STACK.md` for a detailed list):

*   **Backend:** Python 3.13, FastAPI, PostgreSQL, TimescaleDB, Redis, SQLAlchemy, Alembic, Uvicorn.
*   **Frontend:** Vue.js 2, Vuex 3, Axios, JavaScript (ES6+), HTML5, CSS3.
*   **Data Handling:** Pandas (CSV processing), JSON.
*   **Development Environment:** Docker, Docker Compose.

## 3. Key Architectural Decisions & Implementations

This section details major architectural solutions and significant technical implementations.

### 3.1. Backend Architecture (FastAPI)

*   **Framework:** FastAPI was chosen for its asynchronous capabilities, performance, Pydantic-based data validation, and automatic API documentation.
*   **Modular Structure:**
    *   `app/main.py`: Main application entry point, includes routers.
    *   `app/config.py`: Pydantic-based settings management, loading from a root `.env` file.
    *   `app/database.py`: SQLAlchemy engine and session management (`SessionLocal`).
    *   `app/models.py`: SQLAlchemy ORM models (e.g., `User`, `Kline`, `NewsArticle`, `TradeNote`).
    *   `app/schemas.py`: Pydantic schemas for request/response validation and serialization.
    *   `app/crud.py`: Reusable Create, Read, Update, Delete database operations.
    *   `app/routers/`: Directory for API route modules (e.g., `auth.py`, `users.py`, `data.py`, `news.py`). (Perflogs router to be added)
    *   `app/security.py`: Password hashing, JWT creation, and token validation utilities.
    *   `app/redis_utils.py`: Utility for establishing and managing Redis connections.
*   **User Authentication:**
    *   JWT (JSON Web Tokens) are used for securing endpoints.
    *   Passwords are hashed using `bcrypt` (via `passlib`).
    *   Login via nickname or email.
    *   Registration creates a new user, sets `first_joined_at` automatically.
*   **Data Endpoints (Selected):**
    *   `/auth/register`, `/auth/login`: For user authentication.
    *   `/users/me`: Protected endpoint to fetch authenticated user details.
    *   `/data/upload_csv`: Endpoint for unauthenticated users to upload OHLCV CSV files.
    *   `/data/klines/{symbol}/{timeframe}` (GET): Endpoint for fetching historical kline data.
    *   `/ws/klines/{symbol}/{timeframe}` (WebSocket): Endpoint for streaming live kline updates.
    *   `/api/news/{symbol}` (GET): Endpoint for fetching news articles.
    *   (Perflogs API endpoints for `TradeNote` CRUD operations will be added under a `/perflogs/` prefix).
*   **`.env` Configuration:** All sensitive configurations are managed via a `.env` file in the project root.

### 3.2. Database (PostgreSQL with TimescaleDB Extension)

*   **Primary Database:** PostgreSQL.
*   **Time-Series Data:** TimescaleDB extension for `klines` data.
*   **Dockerization:** PostgreSQL/TimescaleDB and Redis run as Docker containers.
*   **Schema Migrations (Alembic):** Alembic manages database schema changes.
*   **Table Structures:**
    *   **`users` Table:** Stores user information, including authentication and subscription details.
        *   `id` (Integer, Primary Key)
        *   `nickname` (String, Unique, Indexed)
        *   `email` (String, Unique, Indexed)
        *   `hashed_password` (String)
        *   `is_active` (Boolean, default True)
        *   `first_joined_at` (TIMESTAMP with timezone, default current_timestamp)
        *   `subscription_plan` (Enum `SubscriptionPlanEnum` ['FREE', 'PREMIUM', 'ULTIMATE'], default 'FREE')
        *   `start_of_subscription` (TIMESTAMP with timezone, nullable)
        *   `end_of_subscription` (TIMESTAMP with timezone, nullable)
    *   **`klines` Table (TimescaleDB Hypertable):** Stores OHLCV data.
        *   `symbol` (String)
        *   `timeframe` (String)
        *   `open_time` (BigInteger, Unix ms) - **Partitioning Column**
        *   `open_price`, `high_price`, `low_price`, `close_price`, `volume` (Numeric)
        *   ... (other kline fields)
        *   **Primary Key:** Composite `(symbol, timeframe, open_time)`.
    *   **`news_articles` Table:** Stores news articles.
        *   `id` (Integer, Primary Key)
        *   `external_article_id` (String, Unique)
        *   `symbol` (String, Indexed)
        *   `headline`, `snippet`, `source_name`, `article_url`, `image_url` (String/Text)
        *   `published_at` (TIMESTAMP with timezone)
        *   `sentiment_score_external`, `sentiment_category_derived` (Float/String, Nullable)
        *   `fetched_at`, `updated_at` (TIMESTAMP with timezone)
    *   **`tradenotes` Table:** Stores user-submitted trade performance logs for the "Perflogs" feature.
        *   `id` (Integer, Primary Key, autoincrement)
        *   `user_id` (Integer, ForeignKey to `users.id`, nullable=False)
        *   `asset_ticker` (String(20), nullable=False, index=True) - e.g., "BTCUSDT"
        *   `timeframe` (String(10), nullable=False) - e.g., "15m"
        *   `trade_direction` (Enum `TradeDirectionEnum` ['long', 'short'], nullable=False) - Stored as PostgreSQL ENUM `tradedirectionenum`.
        *   `entry_price` (Numeric(20, 10), nullable=False)
        *   `exit_price` (Numeric(20, 10), nullable=False)
        *   `margin` (Numeric(20, 10), nullable=False)
        *   `leverage` (Numeric(8, 2), nullable=False, server_default="1.0")
        *   `pnl` (Numeric(20, 10), nullable=False) - Profit and Loss for the trade.
        *   `note_text` (Text, nullable=True) - User's textual note, max 1000 chars.
        *   `created_at` (TIMESTAMP(timezone=True), server_default=func.now())
        *   `updated_at` (TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
        *   **Indexes:** `ix_tradenotes_user_id_asset_ticker` on (`user_id`, `asset_ticker`).

### 3.3. Data Ingestion & Background Services

*   **Kline Data Ingestion Service (`backend/data_ingestion_service/main.py`):**
    *   Standalone asynchronous Python service.
    *   Fetches live kline data from Binance via WebSockets (`websockets` library).
    *   Fetches historical kline data from Binance REST API (`httpx`).
    *   Performs gap detection and backfilling.
    *   Processes and stores klines in TimescaleDB (`klines` table).
    *   Caches recent klines in Redis (sorted set).
    *   Publishes live kline updates to a Redis Pub/Sub channel.
*   **News Fetcher Service (`backend/news_fetcher_service/main.py`):**
    *   Standalone asynchronous Python service.
    *   Fetches news articles from Marketaux API (or others like NewsData.io, CoinDesk, configurable).
    *   Performs sentiment analysis (API-provided or VADER-calculated).
    *   Stores articles in the `news_articles` table.

### 3.4. Frontend Architecture (Vue.js 2 with Local `trading-vue-js`)

*   **Framework:** Vue.js 2, Vuex 3, Vue Router.
*   **Local `trading-vue-js` Integration:** Uses local "raw" version from `frontend/src/trading-vue-core/`.
*   **State Management (Vuex):**
    *   `auth` module: User authentication and details.
    *   `chart` module: `DataCube` management for chart data (OHLCV, signals, live data), current display asset/timeframe.
    *   `news` module: News articles for the "Quick Look" panel.
    *   `perflogs` module: Manages state for the Perflogs feature.
*   **Key Components:**
    *   `Home.vue`: Main view with chart, uploaders, and controls. The top bar is structured with:
        *   A left section (`mode-asset-controls`) containing: "Home" link, `AssetTimeframeSelector` component, and Live/Custom chart mode buttons.
        *   A right section (`user-controls`) containing: "News" toggle, "Perflogs" toggle, user greeting ("Hello, {{nickname}}!"), and "Log out" button. A "Log in" button is displayed in this section if the user is not authenticated.
    *   `CsvUpload.vue`, `SignalUpload.vue`: For custom data uploads.
    *   `Login.vue`, `Register.vue`: Authentication views.
    *   `NewsPanel.vue`: Displays news articles.
    *   `PerflogsPanel.vue`, `TradeNoteCard.vue`, `AddTradeNoteForm.vue`: For the Perflogs feature.
    *   `AssetTimeframeSelector.vue`: Component for selecting asset and timeframe, emits update events.
*   **Charting & Data Display:**
    *   Handles OHLCV and signal data from user uploads.
    *   Integrates live kline data from backend (historical API + WebSocket).
    *   "Live" vs. "Custom" chart modes.
    *   Performance optimizations (crosshair throttling, signal overlay culling).
    *   Interactive asset and timeframe selectors that update chart data and context for other panels (News, Perflogs).
*   **Browser Tab Title:** The application's title displayed in the browser tab is set to "InCharts" via `frontend/public/index.html`.

### 3.5. Perflogs Feature (Backend Foundation - In Progress)

The "Perflogs" feature allows registered users to log their trade performance for backtesting analysis.

#### 3.5.1. Backend (FastAPI, SQLAlchemy, Pydantic)

*   **Database Model (`TradeNote`):**
    *   Defined in `backend/app/models.py` (see details in section 3.2).
    *   Includes fields for asset, timeframe, direction, entry/exit prices, margin, leverage, PnL, and user notes.
    *   Uses a PostgreSQL ENUM `tradedirectionenum` ('long', 'short').
    *   Migration `64cf476d46db` created the table and ENUM type.
*   **Pydantic Schemas (`TradeNoteBase`, `TradeNoteCreate`, `TradeNoteRead`):**
    *   Defined in `backend/app/schemas.py`.
    *   `TradeNoteBase`: Common fields for creation/reading with validation.
    *   `TradeNoteCreate`: For creating new notes.
    *   `TradeNoteRead`: For reading notes, includes `id`, `user_id`, `created_at`, `updated_at`.
    *   JSON encoders handle `Decimal` to `float` and `datetime` to millisecond timestamps.
*   **CRUD Operations:**
    *   Implemented in `backend/app/crud.py`:
        *   `create_trade_note(...)`: Creates a new trade note for a user.
        *   `get_trade_notes_by_user_and_asset(...)`: Retrieves notes for a specific user and asset.
        *   `get_trade_note_by_id(...)`: Retrieves a specific note by ID, ensuring user ownership.
        *   `delete_trade_note(...)`: Deletes a note, ensuring user ownership.
*   **API Endpoints (Implemented in `backend/app/routers/perflogs.py` under `/perflogs` prefix):**
    *   `POST /notes/`: Create a new trade note (authenticated).
    *   `GET /notes/{asset_ticker}`: Get notes for user and asset (authenticated).
    *   `DELETE /notes/{trade_note_id}`: Delete a note (authenticated, ownership).

#### 3.5.2. Frontend (Vue.js 2, Vuex)

*   **Vuex Module (`frontend/src/store/modules/perflogs.js`):**
    *   Manages state for trade notes (list, loading status, errors), current asset context.
    *   Actions for fetching, creating, and deleting trade notes via API calls.
    *   Getters for sorted notes, total P&L, and date range.
*   **Key Components:**
    *   `PerflogsPanel.vue` (`frontend/src/components/PerflogsPanel.vue`):
        *   Main container for the Perflogs feature, displayed as a right sidebar.
        *   Toggled via a button in `Home.vue`.
        *   Displays summary P&L, date range, and a list of trade notes for the currently selected asset on the chart.
        *   Includes an "Add Note" button to open the `AddTradeNoteForm.vue`.
        *   Handles data fetching and clearing based on asset context changes.
        *   Styling: Dark theme, consistent with the application. Uses Font Awesome for icons (close button).
        *   "No trade notes recorded..." message is styled with an orange warning theme.
        *   Total P&L for zero is displayed neutrally.
    *   `TradeNoteCard.vue` (`frontend/src/components/TradeNoteCard.vue`):
        *   Displays individual trade note details (asset, direction, entry/exit, P&L, etc.).
        *   Includes a delete button (with Font Awesome icon).
        *   Supports expanding/collapsing longer note texts.
        *   Styling: Dark theme, card-based layout with rounded corners.
    *   `AddTradeNoteForm.vue` (`frontend/src/components/AddTradeNoteForm.vue`):
        *   A form for users to input new trade note details.
        *   Includes fields for direction, prices, margin, leverage, and a text note.
        *   Performs client-side P&L calculation.
        *   Handles form submission and cancellation.
*   **Icon Integration (Font Awesome):**
    *   Font Awesome 5 is integrated via a CDN link in `frontend/public/index.html` to provide icons (e.g., delete, close, add).
*   **Styling and UI Considerations:**
    *   The Perflogs panel and its components are styled to maintain consistency with the overall dark theme of the application.
    *   Emphasis on clear presentation of trade data and user-friendly interactions for adding and managing notes.
    *   Responsive data clearing and context updates when the chart's asset changes or the panel is closed/opened.
    *   The "Add Note" button is disabled if no asset is selected on the chart.

## 4. Running the Project

### 4.1. Dockerized Services (Redis & TimescaleDB)

The primary database (TimescaleDB/PostgreSQL) and cache (Redis) are managed via Docker Compose for a consistent development environment.

1.  **Prerequisites:** Docker Desktop (or Docker Engine for Linux) must be installed and running.
2.  **Navigate to Project Root:** Ensure your terminal is in the root directory of the project (e.g., `/path/to/inchart-seed-test2`).
3.  **Start Services in Detached Mode:**
    ```bash
    docker-compose up -d
    ```
    *   This command starts (or creates if they don't exist) the `inchart_redis` and `inchart_postgres_timescaledb` services as defined in your `docker-compose.yml` file.
    *   The `-d` flag runs the containers in the background (detached mode).
    *   Redis will be accessible on `localhost:6379` (or as configured).
    *   TimescaleDB/PostgreSQL will be accessible on `localhost:5433` (or as configured).
    *   Data persistence is enabled via named volumes (e.g., `postgres_timescaledb_data`, `redis_data`), so your data will remain even if containers are stopped and restarted, unless volumes are explicitly removed.
4.  **View Service Logs (Optional but Recommended for Troubleshooting):**
    To view logs for Redis:
    ```bash
    docker-compose logs -f inchart_redis
    ```
    To view logs for TimescaleDB/PostgreSQL:
    ```bash
    docker-compose logs -f inchart_postgres_timescaledb
    ```
    The `-f` flag follows the log output. Press `Ctrl+C` to stop following.
5.  **Stop Services:**
    ```bash
    docker-compose down
    ```
    *   This command stops and removes the containers defined in `docker-compose.yml`.
    *   **Important:** This command *does not* remove the persistent data volumes by default. To also remove data volumes (resulting in data loss), you would use `docker-compose down -v`.

### 4.2. Backend (FastAPI Application)

1.  **Prerequisites:** Python 3.13, virtual environment set up (e.g., in `backend/.venv/`).
2.  **Navigate to Backend Directory:** `cd /path/to/inchart-seed-test2/backend`
3.  **Activate Virtual Environment:** (Example for bash/zsh)
    ```bash
    source .venv/bin/activate
    ```
4.  **Install Dependencies (if not already done or `requirements.txt` updated):**
    ```bash
    pip install -r ../requirements.txt 
    ```
    (Note: `../requirements.txt` assumes `requirements.txt` is in the project root, adjust if it's `backend/requirements.txt`)
5.  **Ensure `.env` File:** A `.env` file must exist in the project root (`/path/to/inchart-seed-test2/.env`) with necessary configurations like `DATABASE_URL` (pointing to `postgresql://inchart_admin:p3ace-0f-ouR-t!me@localhost:5433/inchart_db`), `REDIS_HOST`, `REDIS_PORT`, etc.
6.  **Run Alembic Migrations (if new migrations exist or setting up DB for the first time):**
    ```bash
    alembic upgrade head
    ```
7.  **Start FastAPI Server:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The API will be accessible at `http://localhost:8000` and docs at `http://localhost:8000/docs`.

### 4.3. Data Ingestion Service (Standalone Python Process)

This service is responsible for fetching live and historical kline data from Binance, processing it, and storing it in TimescaleDB and Redis.

1.  **Prerequisites:**
    *   Python 3.13 and the project's virtual environment (e.g., in `backend/.venv/`) must be set up with all dependencies installed (see Backend setup 4.2).
    *   The Dockerized services (Redis & TimescaleDB from step 4.1) **must be running**.
    *   The `.env` file in the project root must be correctly configured with `REDIS_HOST`, `REDIS_PORT`, `DATABASE_URL` (for TimescaleDB), `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`, `PROACTIVE_SYMBOLS`, `PROACTIVE_TIMEFRAMES`.
2.  **Navigate to Backend Directory:** `cd /path/to/inchart-seed-test2/backend`
3.  **Activate Virtual Environment:** (Example for bash/zsh)
    ```bash
    source .venv/bin/activate
    ```
4.  **Start the Service:**
    ```bash
    python -m data_ingestion_service.main
    ```
    *   The service will start logging to the console.
    *   It will begin backfilling historical data for configured symbols/timeframes if needed.
    *   It will then connect to Binance WebSockets for live data.
5.  **To Stop the Service:** Press `Ctrl+C` in the terminal where it's running. The service should attempt a graceful shutdown.

### 4.4. News Fetcher Service (Standalone Python Process)

This service is responsible for periodically fetching news articles.

1.  **Prerequisites:**
    *   Python 3.13 and the project's virtual environment (e.g., in `backend/.venv/`) must be set up with all dependencies installed.
    *   The Dockerized TimescaleDB service **must be running**.
    *   The `.env` file in the project root must be correctly configured with `DATABASE_URL` and relevant news API keys (e.g., `MARKETAUX_API_TOKEN`).
2.  **Navigate to Backend Directory:** `cd /path/to/inchart-seed-test2/backend`
3.  **Activate Virtual Environment:**
    ```bash
    source .venv/bin/activate
    ```
4.  **Start the Service:**
    ```bash
    python -m news_fetcher_service.main
    ```
    *   The service will start logging to the console and begin fetching news.
5.  **To Stop the Service:** Press `Ctrl+C`.

### 4.5. Frontend (Vue.js Application)

1.  **Prerequisites:** Node.js and npm installed.
2.  **Navigate to Frontend Directory:** `cd /path/to/inchart-seed-test2/frontend`
3.  **Install Dependencies (if not already done):**
    ```bash
    npm install
    ```
4.  **Start Development Server:**
    ```bash
    npm run serve
    ```
    The frontend will be accessible at `http://localhost:8080` (or another port if 8080 is busy). The browser tab will display "InCharts".

## 5. Key Environment Variables (`.env` file in project root)

*   `DATABASE_URL`: SQLAlchemy connection string for PostgreSQL/TimescaleDB (e.g., `postgresql://inchart_admin:p3ace-0f-ouR-t!me@localhost:5433/inchart_db`)
*   `REDIS_HOST`: Redis server hostname (e.g., `localhost`)
*   `REDIS_PORT`: Redis server port (e.g., `6379`)
*   `SECRET_KEY`: Secret key for JWT token generation (a long random string).
*   `ALGORITHM`: Algorithm for JWT (e.g., `HS256`).
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT access token expiry time in minutes.
*   `BINANCE_API_KEY`: (Optional) Binance API key for historical data fetching.
*   `BINANCE_SECRET_KEY`: (Optional) Binance API secret key.
*   `PROACTIVE_SYMBOLS`: Comma-separated list of symbols for live kline ingestion (e.g., `BTCUSDT,ETHUSDT`).
*   `PROACTIVE_TIMEFRAMES`: Comma-separated list of timeframes for live kline ingestion (e.g., `1m,5m,1h`).
*   `INITIAL_BACKFILL_DAYS`: Number of days to backfill for new symbols (e.g., `90`).
*   `MAX_KLINES_IN_REDIS`: Max number of klines to keep in Redis cache per symbol/timeframe (e.g., `2000`).
*   `API_REDIS_LOOKBACK_MS`: How far back (in ms) the API should check Redis for klines (e.g., `86400000` for 1 day).
*   `MARKETAUX_API_TOKEN`: API token for Marketaux news service.
*   (Other API tokens like `NEWSDATA_IO_API_TOKEN`, `COINDESK_API_TOKEN` if those services are used by `news_fetcher_service`).

## 6. Database Inspection and Management

### 6.1. Accessing Dockerized PostgreSQL/TimescaleDB CLI

To directly interact with the PostgreSQL database running in the `inchart_postgres_timescaledb` Docker container (e.g., for manual queries or inspection), you can use `psql`:

1.  **Ensure the container is running:** `docker-compose ps` should show `inchart_postgres_timescaledb` as "Up".
2.  **Connect using `docker exec`:**
    ```bash
    docker exec -it inchart_postgres_timescaledb psql -U inchart_admin -d inchart_db
    ```
    *   Replace `inchart_admin` with your database username and `inchart_db` with your database name if they differ from the common project defaults (check your `.env` or `docker-compose.yml`).
    *   You will be prompted for the `inchart_admin`'s password.
    *   You are now in the `psql` interactive terminal.

3.  **Example: Inspecting an Enum Type (e.g., `tradedirectionenum`):**
    ```sql
    SELECT unnest(enum_range(NULL::tradedirectionenum));
    ```
    This will list the labels defined for the `tradedirectionenum` type.

4.  **Listing all ENUM types and their labels:**
    ```sql
    SELECT t.typname AS enum_name, e.enumlabel AS enum_value
    FROM pg_type t 
    JOIN pg_enum e ON t.oid = e.enumtypid  
    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'public' -- Or your specific schema if not public
    ORDER BY enum_name, e.enumsortorder;
    ```

5.  **Exiting `psql`:** Type `\q` and press Enter.