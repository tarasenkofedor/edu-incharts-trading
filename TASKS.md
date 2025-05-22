# InChart Project Tasks

This document outlines all development tasks for the InChart MVP. Tasks are managed according to `project_guidelines/TASK_RULES.md` (once created/if applicable).

**IMPORTANT NOTE ON FRONTEND CHARTING (User Instruction Clarification):**
The user has specified that **NO direct installation of the `trading-vue-js` library from an external package manager (like npm) is allowed.** Instead, the project MUST use the existing local "raw" frontend code and components found within this project's structure, specifically the contents of the `src/` and `dist/` directories (which appear to be the source and distributed files of a version of `trading-vue-js`). The `docs/` directory contains documentation for this local version. Tasks 2.0, 2.1, 2.2, 2.3, and 2.4 will proceed with the understanding that they need to integrate and utilize these local files for all charting functionalities. This means Vue.js project setup (Task 2.1) should not attempt to `npm install trading-vue-js`.

---

## 1.0 Foundational Setup & User Accounts
   - **Status:** `done`
   - **Description:** Setup backend (FastAPI), database (PostgreSQL with Alembic for migrations), and implement basic user registration and login with JWT authentication.
   - **Dependencies:** None

   ### 1.1 Backend Project Initialization (FastAPI)
      - **Status:** `done`
      - **Description:** Create FastAPI project structure, basic configuration, and dependencies (`uvicorn`, `psycopg2-binary`, `passlib[bcrypt]`, `python-jose[cryptography]`, `alembic`, `sqlalchemy`).
   ### 1.2 Database Setup (PostgreSQL & Alembic)
      - **Status:** `done`
      - **Description:** Define User model (fields: `id`, `nickname`, `email`, `hashed_password`, `is_active`, `first_joined_at`, `subscription_plan`, `start_of_subscription`, `end_of_subscription`). Setup database connection in FastAPI. Initialize Alembic for migrations and create the initial migration for the `users` table.
   ### 1.3 User Registration Endpoint
      - **Status:** `done`
      - **Description:** Implement `/auth/register` endpoint. Accepts user details (as per model), stores hashed password, returns JWT.
   ### 1.4 User Login Endpoint
      - **Status:** `done`
      - **Description:** Implement `/auth/login` endpoint. Accepts credentials (e.g., nickname/email and password), verifies credentials, returns JWT.
   ### 1.5 JWT Authentication Middleware/Dependencies
      - **Status:** `done`
      - **Description:** Implement JWT token generation, validation, and secure endpoint dependencies in FastAPI.
   ### 1.6 Database Migrations with Alembic (Covered by 1.2 for initial, further tasks if needed)
      - **Status:** `done`
      - **Description:** Alembic is correctly set up. The initial `users` table migration, including complex ENUM handling, has been successfully implemented and applied after resolving several issues. This task can be considered complete for the initial schema. Future schema changes will generate new migrations.

## 2.0 Core Charting Shell (Vue.js & Local `trading-vue-js` Code)
   - **Status:** `done`
   - **Description:** Integrate the local `trading-vue-js` code (from `src/` and `dist/`) into a new Vue.js application. Create the basic UI shell including the unified asset/timeframe selection component. **(Utilize local files as per "IMPORTANT NOTE ON FRONTEND CHARTING" above)**.
   - **Dependencies:** 1.0

   ### 2.1 Vue.js Project Setup
      - **Status:** `done`
      - **Description:** Initialize Vue.js (v2) project. Install `axios`, and `vuex@3` (as Vuex 4 is for Vue 3). **(Ensure NO `trading-vue-js` is installed from npm; we will use local files).**
      - **User confirmed Vue CLI v5.0.8.**
      - **User renamed `frontend/src` to `frontend/src_trading_vue_local`, `frontend/dist` to `frontend/dist_trading_vue_local`, `frontend/docs` to `frontend/docs_trading_vue_local`.**
      - **Successfully ran `cd frontend && vue create .` (Vue 2, Babel, Router, Vuex, Linter).**
      - **Installed `axios` and `vuex@3` in `frontend/`.**
      - **Created `frontend/src/trading-vue-core/` for the local `trading-vue-js` source.**
      - **Next:** User to move local `trading-vue-js` files (`src_trading_vue_local`, `docs_trading_vue_local`) into the new project structure. Awaiting clarification on `dist_trading_vue_local`.
      - **Update (2025-05-18):** `frontend/dist_trading_vue_local/` contains built bundles, not essential raw assets. It likely won't be needed for integration. The focus is now on using the source from `frontend/src/trading-vue-core/`.
      - **User confirmed file moves are complete (assumed based on recent interaction). Main `TradingVue` component identified from `frontend/src/trading-vue-core/`**
   ### 2.2 Basic Charting Component Integration
      - **Status:** `done`
      - **Description:** Create a main view/component (`frontend/src/views/Home.vue`) that embeds the local `TradingVue.vue` charting component. Populate with minimal static data (`frontend/src/assets/data.json`) to verify rendering. **(Utilized local files as per "IMPORTANT NOTE ON FRONTEND CHARTING" above)**.
   ### 2.3 Asset/Timeframe UI Component (Static)
      - **Status:** `done`
      - **Description:** Design and implement the UI for the asset/timeframe selector in the top-left of the chart area. Initially, it will be static (displaying placeholders, non-functional clicks). Added to `frontend/src/views/Home.vue`.
      - **Styling:** Minimalistic, Apple-like design.
   ### 2.4 Fix Chart Zoom Functionality
      - **Status:** `DELETED/RESOLVED`
      - **Description:** Investigate and fix issues with chart zoom functionality (mouse wheel/trackpad). The root cause was `MIN_ZOOM` in `trading-vue-core/components/js/grid.js` being too high for the small sample dataset (5 data points vs. `MIN_ZOOM` of 25). Setting `MIN_ZOOM` to 1 resolved this. This learning is documented in `DIARY.md`.
   ### 2.5 Store Chart Data in Vuex
      - **Status:** `done`
      - **Description:** Refactor `Home.vue` to fetch and manage chart data (from `assets/data.json` for now) through Vuex store. Create necessary Vuex modules, state, getters, mutations, and actions.

## 3.0 Custom Price Data (OHLCV) Upload & Display
   - **Status:** `done`
   - **Description:** Implement frontend UI for CSV upload, backend processing (validation, storage/forwarding), and display of custom OHLCV data on the chart. Allows unauthenticated users to upload and view their own price data. Timestamp and initial display issues resolved. Logs cleaned up. Potential minor lagginess to monitor.
   - **Dependencies:** 2.2

   ### 3.1 Frontend Price Data Upload UI
      - **Status:** `done`
      - **Description:** Create Vue component (`frontend/src/components/CsvUpload.vue`) for CSV file input for OHLCV data. Integrate into `Home.vue`.
   ### 3.2 Backend API Endpoint for Price Data Upload
      - **Status:** `done`
      - **Description:** Create FastAPI endpoint (`/data/upload_csv` in `backend/app/routers/data.py`) to receive OHLCV CSV. Validate format (`timestamp,open,high,low,close,volume`), ensure timestamps are sorted ascending and in a recognized format (numeric MS preferred), check numeric types for OHLCV. Convert timestamps to ms. Returns processed data.
   ### 3.3 Chart Population with Custom Price Data
      - **Status:** `done`
      - **Description:** Frontend logic to send uploaded CSV to backend, receive processed data, and update the chart data object via Vuex store. Timestamp issues resolved.
          - `CsvUpload.vue` emits `file-upload-initiated`.
          - `Home.vue` handles event, uses `axios` to POST to `/data/upload_csv`.
          - On success, `Home.vue` calls Vuex action `chart/setUploadedChartData` with backend data.
          - Vuex module `chart.js` updated with `setUploadedChartData` action and refined `SET_CHART_DATA` mutation to handle data types for `DataCube`.
          - `Home.vue` calls `chart/loadInitialChartData` on mount.

## 3.5 User Authentication UI & Nickname Integration
   - **Status:** `done`
   - **Description:** Implement UI components for user login and registration, integrate them with the Vuex store, and ensure nickname functionality is consistent with the updated User model.
   - **Dependencies:** 1.0, Vuex Store Setup (implicitly done alongside Task 2.1 or as needed)

   ### 3.5.1 Login Component Enhancements for Nickname
      - **Status:** `done`
      - **Description:** Update/Create Vue component for user login to use `nickname` (or email) as per backend auth. On submit, dispatch Vuex 'login' action. Handle success/error responses. Integrated auto-login, navigation guards, and dynamic display of user info in `App.vue`.
   ### 3.5.2 Registration Component Enhancements for Nickname
      - **Status:** `done`
      - **Description:** Created `Register.vue` component with fields for nickname, email, and password. Component dispatches Vuex action for registration and then login for auto-login.
   ### 3.5.2.1 Create Vuex action for registration
      - **Status:** `done`
      - **Description:** Added `register` action to `auth.js` Vuex module. It calls the backend `/auth/register` endpoint and handles API response/errors.
   ### 3.5.2.2 Implement auto-login after successful registration
      - **Status:** `done`
      - **Description:** `Register.vue` now calls the `login` Vuex action immediately after a successful `register` action, effectively auto-logging in the user.
   ### 3.5.2.3 Enhance error handling and user feedback in Register component
      - **Status:** `done`
      - **Description:** `Register.vue` displays error messages from the Vuex store (populated by `register` or `login` actions) and handles password mismatch locally.
   ### 3.5.3 Display User Nickname / Logout Button
      - **Status:** `done`
      - **Description:** Implement UI elements to display user login status (e.g., show user nickname if logged in) and a logout button that dispatches the Vuex 'logout' action. (This was completed as part of 3.5.1 work in `App.vue`).
   ### 3.5.4 Backend: Update User Model & Schemas for Full Schema
      - **Status:** `done`
      - **Description:** Ensure User SQLAlchemy model and Pydantic schemas (`UserCreate`, `User` response, `TokenData` if needed) align with the full required schema: `id`, `nickname`, `email`, `hashed_password`, `is_active`, `first_joined_at`, `subscription_plan`, `start_of_subscription`, `end_of_subscription`. (This task consolidates and ensures completeness based on Task 1.2, which was already done with all fields).
      - **Dependencies:** 1.2
   ### 3.5.5 Backend: Update Registration Logic for Full Schema
      - **Status:** `done`
      - **Description:** Modify `/auth/register` endpoint to accept all required fields for user creation (e.g., `nickname`, `email`, `password`), validate uniqueness for relevant fields (e.g., `nickname`, `email`), and store them. `first_joined_at` should be set automatically. Other fields like subscription details might be optional at registration or handled later. (Backend part already handled in 1.3 and 1.2).
      - **Dependencies:** 1.3, 3.5.4
   ### 3.5.6 Backend: Update Login Logic for Nickname/Email
      - **Status:** `done`
      - **Description:** Modify `/auth/login` endpoint to allow authentication via `nickname` and password, or `email` and password. (Backend part already handled in 1.4).
      - **Dependencies:** 1.4, 3.5.4

## 4.0 Custom Signal Data Upload & Display
   - **Status:** `done`
   - **Description:** Implement functionality for users to upload custom signal data (e.g., buy/sell markers, indicator values) and display them on the chart as overlays. Resolved issues with signal parsing and display on the chart.
   - **Dependencies:** 2.2, Potentially 1.0 (if signals are user-specific and stored)

   ### 4.1 Frontend UI for Signal Data Upload
      - **Status:** `done`
      - **Description:** Create a Vue component (`frontend/src/components/SignalUpload.vue`) for uploading signal data via CSV. Integrated into `Home.vue`.
      - **Dependencies:** None directly, but interacts with 3.3 logic.

   ### 4.2 Backend API Endpoint for Signal Data Upload
      - **Status:** `not_needed_for_mvp`
      - **Description:** Create a FastAPI endpoint to receive signal data. Validate the format. For MVP, signal data is handled entirely client-side and is not persistent on the backend.
      - **Dependencies:** None directly.

   ### 4.3 Chart Population with Custom Signal Data
      - **Status:** `done`
      - **Description:** Frontend logic to parse uploaded signal CSV (`SignalUpload.vue`), transform it into "Trades" overlay format, and update the chart data object via Vuex store (`chart.js`). Resolved issues with `DataCube` updates and `Chart.vue` overlay rendering.
      - **Dependencies:** 2.2, 4.1

   ### 4.4 Refine Uploader UX and Error Handling (OHLCV & Signals)
      - **Status:** `done`
      - **Description:** Standardize message styling, client-side header validation, and error feedback for both `CsvUpload.vue` and `SignalUpload.vue` components. Clean up console logs.
      - **Dependencies:** 3.1, 4.1

   ### 4.5 ESLint & Parsing Fixes for SignalUploader
      - **Status:** `done`
      - **Description:** Resolved ESLint errors (formatting, `no-async-promise-executor`) in `SignalUpload.vue`. Fixed a bug causing incorrect parsing of valid signal CSVs due to newline handling (`split('\n')` fix).
      - **Dependencies:** 4.1, 4.3

## 5.0 Advanced Charting Features & Data Management
   - **Status:** `to_do`
   - **Description:** (Placeholder for future advanced features beyond live data integration. Specific sub-tasks to be defined later.)
   - **Dependencies:** 6.0 (Likely, as live data is a core advanced feature)

## 6.0 Live Price Data Integration (Binance)
   - **Status:** `done`
   - **Description:** Implement the pipeline for ingesting, storing, caching, and serving live and historical price data from Binance using WebSockets, TimescaleDB, and Redis. This includes setting up TimescaleDB and Redis, creating background workers for data ingestion, and integrating data fetching into the frontend with a mode switch for 'Live' vs. 'Custom' data.
   - **Dependencies:** 2.0, 1.0

   ### 6.1 Environment & Infrastructure Setup
      - **Status:** `done`
      - **Description:** Prepare the backend environment and database for live data.
      - **6.1.0 Install Docker Desktop (macOS):**
         - **Status:** `done`
         - **Description:** Download and install Docker Desktop for macOS from the official Docker website. Ensure the Docker engine is running.
      - **6.1.1 Setup Redis Server (via Docker):**
         - **Status:** `done`
         - **Description:** Create a `docker-compose.yml` file (or update an existing one) in the project root to define a Redis service. Run Redis in a Docker container for development. Configure FastAPI to connect to this Dockerized Redis instance.
      - **6.1.2 Setup TimescaleDB (via Docker):**
         - **Status:** `done`
         - **Description:** Update `docker-compose.yml` to define a PostgreSQL service with the TimescaleDB extension enabled (using an appropriate Docker image like `timescale/timescaledb:latest-pg16`). Run TimescaleDB in a Docker container for development. Ensure it's configured for data persistence.
      - **6.1.3 Backend Project Configuration:**
         - **Status:** `done`
         - **Description:** Update `backend/app/config.py` to load Redis and Binance API connection details from `.env`.
      - **6.1.4 Define Kline Data Model & Migration (TimescaleDB):**
         - **Status:** `done`
         - **Description:** Define SQLAlchemy model for Kline data. Generate and apply Alembic migration to create `klines` table, configure it as a TimescaleDB hypertable partitioned by `open_time`, ensuring PK includes partitioning column.
      - **6.1.5 Implement Redis Connection Utility:**
         - **Status:** `done`
         - **Description:** Develop a utility to manage Redis connections and caching for live data. Added `redis` to `requirements.txt`, created `backend/app/redis_utils.py` with `get_redis_connection` and `ping_redis` functions. Made `get_redis_connection` available via `backend/app/__init__.py`.

   ### 6.2 Backend: Data Ingestion Service (Background Worker/Process)
      - **Status:** `done`
      - **Description:** Develop a separate, resilient background worker process for ingesting data from Binance.
      - **6.2.1 Ingestion Service Structure:**
         - **Status:** `done`
         - **Description:** Design and implement a separate Python process/script for data ingestion (outside of FastAPI app). This worker will manage WebSocket connections, process data, and handle persistence. Created `backend/data_ingestion_service/` with `main.py` (entry point, basic setup, graceful shutdown) and `service_utils.py` (logging).
      - **6.2.2 Binance WebSocket Connector Module:**
         - **Status:** `done`
         - **Description:** Develop a module to establish and manage multiplexed WebSocket connections to Binance for kline streams (e.g., `<symbol>@kline_<interval>`). Implement robust reconnection logic with exponential backoff and handle connection lifecycle events. Created `BinanceWebSocketManager` class in `backend/data_ingestion_service/binance_connector.py` and integrated its use into `main.py` for proactive symbol/timeframe tracking.
      - **6.2.3 Live Data Processing & Persistence Pipeline:**
         - **Status:** `done`
         - **Description:** Implemented `kline_data_processor` in `backend/data_ingestion_service/main.py`. On receiving a kline: maps to `Kline` model, saves to TimescaleDB (via `asyncio.to_thread`, with `ON CONFLICT DO NOTHING`), updates Redis sorted set cache (trimmed, via `asyncio.to_thread`), and publishes to Redis Pub/Sub channel (via `asyncio.to_thread`). Added `MAX_KLINES_IN_REDIS` to config. `SessionLocal` and `redis_client` are passed to the processor.
      - **6.2.4 Proactive Tracking Orchestration:**
         - **Status:** `done`
         - **Description:** Ingestion service reads configured symbols/timeframes from project config (`settings.PROACTIVE_SYMBOLS`, `settings.PROACTIVE_TIMEFRAMES` loaded from `.env`) on startup and maintains active WebSocket subscriptions for these pairs via `BinanceWebSocketManager` instances, as implemented in `backend/data_ingestion_service/main.py`.
      - **6.2.5 Historical Data Backfill Module (Binance REST API):**
         - **Status:** `done`
         - **Description:** Implemented `fetch_historical_klines` and `save_historical_klines_to_db` in `backend/data_ingestion_service/historical_data_fetcher.py`. Fetches from Binance `/api/v3/klines` with pagination, rate limit handling (retries on 429/418), and API key usage. Saves to TimescaleDB with `ON CONFLICT DO NOTHING`.
      - **6.2.6 Gap Detection & Filling Logic:**
         - **Status:** `done`
         - **Description:** Integrated gap detection and filling into `backend/data_ingestion_service/main.py`. On service startup, for each proactive symbol/timeframe: queries DB for latest kline, calculates if a gap exists against current time (with buffer), and uses `historical_data_fetcher` to backfill. Initial backfill for new pairs uses `INITIAL_BACKFILL_DAYS`. Added `_timeframe_to_ms` and `_get_latest_kline_open_time_from_db` helpers. `kline_data_processor` now correctly uses `symbol` and `timeframe` arguments.

   ### 6.3 Backend: API for Frontend Consumption
      - **Status:** `done`
      - **Description:** Expose endpoints for the frontend to fetch kline data.
      - **6.3.1 Kline Data API Endpoint (Historical):**
         - **Status:** `done`
         - **Description:** Create FastAPI endpoint (`/data/klines/{symbol}/{timeframe}`) accepting `start_ms`, `end_ms`, and `limit` for fetching paginated historical data primarily from TimescaleDB. Returns `List[KlineRead]`. Implemented in `backend/app/routers/data.py`.
      - **6.3.2 API Data Retrieval Logic:**
         - **Status:** `done`
         - **Description:** Endpoint logic enhanced. It now checks Redis for recent klines (within `API_REDIS_LOOKBACK_MS`) before querying TimescaleDB, combines and deduplicates results. The ingestion service sets a `backfill_status:<symbol>:<timeframe>` Redis key during historical backfills. The API reads this key and returns the status (e.g., "in_progress", "stale_in_progress") and `backfill_last_updated_ts` in a `KlineHistoricalResponse` object, which wraps the `klines` list.
      - **6.3.3 Backend WebSocket for Live Kline Updates:**
         - **Status:** `done`
         - **Description:** Create a FastAPI WebSocket endpoint (e.g., `/ws/klines/{symbol}/{timeframe}`). When a frontend client connects, this endpoint subscribes to the internal Redis Pub/Sub channel (populated by the Ingestion Service via 6.2.3) for the specified `symbol:timeframe` and relays new klines to the connected frontend client.

   ### 6.4 Frontend: Chart Data Integration & Mode Switching
      - **Status:** `done`
      - **Description:** Integrate live data display, historical data loading, and mode switching ('Live' vs. 'Custom') into the frontend.
      - **6.4.1 Vuex State for Chart Mode & Context:**
         - **Status:** `done`
         - **Description:** Add Vuex state in `chart.js` for `chartMode: 'live' | 'custom'`, `lastLiveAsset`, and `lastLiveTimeframe`. Create mutations/actions to manage this state.
      - **6.4.2 "Chart Type" UI Component in `Home.vue`:**
         - **Status:** `done`
         - **Description:** Implement "Chart Type" selector with "Live" and "Custom" buttons in `Home.vue`. Wire buttons to Vuex actions. Implement conditional visibility for `CsvUpload.vue` (hidden in "Live" mode).
      - **6.4.3 Data Handling on Mode Switch:**
         - **Status:** `done`
         - **Description:** Implement logic in Vuex/`Home.vue` to:
            - **On Switch to "Custom":** Close/ignore live price WebSocket, clear chart, load default mock OHLCV data.
            - **On Switch to "Live":** Clear chart, retrieve/default `lastLiveAsset` & `lastLiveTimeframe`, trigger historical load (6.4.4) and live updates (6.4.5).
      - **6.4.4 Paginated History Loading (Live Mode):**
         - **Status:** `done`
         - **Description:** Modify `Home.vue`/Vuex to fetch historical kline data in chunks from backend API (6.3.1) when in "Live" mode and user pans left or mode is switched to "Live".
      - **6.4.5 Live Price Updates on Chart (Live Mode via Frontend WebSocket):**
         - **Status:** `done`
         - **Description:** Frontend establishes WebSocket connection to backend endpoint (6.3.3) when `chartMode` is "Live". Close connection when switching to "Custom". Update `DataCube` via Vuex with incoming live klines.
      - **6.4.6 Signal Handling Across Modes:**
         - **Status:** `done`
         - **Description:** Ensure `SignalUpload.vue` and Vuex signal logic correctly apply signals to `DataCube` irrespective of `chartMode`. `DataCube` re-initialization during mode switches must be handled correctly.
      - **6.4.7 UI for Data Gaps/Loading States (Live Mode):**
         - **Status:** `done`
         - **Description:** Display visual feedback on chart for historical data chunk loading (Live mode). If API indicates backfill in progress, show persistent user message. (General status indicators).
      - **6.4.8 Frontend UX: Initial Data Preload Window / No Data Pop-up:**
         - **Status:** `done`
         - **Description:** Implement a user-friendly pop-up notification in the bottom-left corner of the chart. This pop-up should appear when the frontend is in 'Live' mode and:
            - There's no kline data initially available for the selected asset/timeframe (e.g., API returns empty, or backfill is extensive).

## 7.0 Testing, Refinement & Documentation
   - **Status:** `in_progress`
   - **Description:** Thoroughly test the new data pipeline and document its components.
   - **7.1 Backend Unit & Integration Tests:**
      - **Status:** `done`
      - **Description:** Write tests for data models, ingestion logic (mocking Binance interactions), API endpoints.
         - Klines API (`/data/klines/{symbol:path}/{timeframe}`):
             - Test DB interaction (data fetching, filtering by limit, start_ms) - `done`
             - Test Redis cache interaction (data only in Redis, data in Redis & DB, backfill status reporting) - `done`
         - WebSocket API (`/ws/klines/{symbol:path}/{timeframe}`):
             - Test successful connection, subscription, message relay, ping/pong, and disconnection. - `done`
             - Test Redis connection failure handling. - `done`
         - Data Ingestion Service:
             - Unit tests for `BinanceWebSocketManager` (connection, message parsing, reconnection, shutdown) - `done`
             - Unit tests for `historical_data_fetcher` (API calls, pagination, rate limits, error handling, DB save mock) - `done`
             - Integration tests for `kline_data_processor` (DB write, Redis cache, Pub/Sub, error handling for each step) - `done`
   - **7.2 Frontend Interaction Testing:**
      - **Status:** `to_do`
      - **Description:** Manually test chart loading, mode switching, panning for history, live updates, and gap/loading indicators for all configured assets/timeframes.
   - **7.3 Performance & Stability Monitoring:**
      - **Status:** `to_do`
      - **Description:** Observe system behavior, especially the ingestion worker and database load.
   - **7.4 Update Project Documentation:**
      - **Status:** `in_progress`
      - **Description:** Document the new data pipeline architecture, configuration options, background worker setup, and API endpoints in `DIARY.md`, `README.md`, and `DOCUMENTATION.md`. This also includes new features like "Quick Look News".
   - **7.5 Frontend Performance Optimizations (`Trades.vue`):**
      - **Status:** `done`
      - **Description:** Optimized the `Trades.vue` overlay component for better rendering performance when displaying multiple signals. Implemented horizontal culling (drawing only visible markers) and zoom-dependent label rendering (drawing labels only when candles are sufficiently wide, based on `layout.px_step`).
      - **Dependencies:** 2.2, 4.3

## 8.0 Feature: "Quick Look" News Panel
   - **Status:** `done`
   - **Description:** Implement a feature to display recent news articles with sentiment for the selected financial asset. News sourced from `marketaux` API. Feature visible to logged-in users.
   - **Dependencies:** 1.0 (User Accounts), `marketaux` API key in `.env`.

   - ### 8.1 Backend: News Data Handling
        - **Status:** `done`
        - **Description:** Setup database storage and a background service to fetch and process news from `marketaux`.

        - **Task QL.B1: Define News Database Model & Migration**
            - **Status:** `done`
            - **Description:** In `backend/app/models.py`, define `NewsArticle` SQLAlchemy model. Fields: `id` (PK), `external_article_id` (unique, from `marketaux`), `symbol` (indexed), `headline`, `snippet`, `source_name`, `article_url`, `image_url` (nullable), `published_at` (DateTime(timezone=True)), `sentiment_score_external` (nullable Float), `sentiment_category_derived` (nullable String: "Positive"/"Neutral"/"Negative"), `fetched_at` (DateTime(timezone=True), server_default=func.now()), `updated_at` (DateTime(timezone=True), server_default=func.now(), onupdate=func.now()). Generate and apply Alembic migration.
        - **Task QL.B2: Implement News Polling Service**
            - **Status:** `done`
            - **Description:** Create `backend/news_fetcher_service/main.py`. Periodically (e.g., ~15 mins) fetch news from `marketaux` for a predefined list of symbols. Parse response (headline, snippet, source, URL, image URL, published time, entity-specific sentiment). Map sentiment score to category. Save new articles to DB, avoid duplicates via `external_article_id`. Add logging. Ensure graceful shutdown. **Note: Currently facing data quality issues (old news, incorrect descriptions).**
        - **Task QL.B2.1: Implement VADER Sentiment Analysis (Configurable)**
            - **Status:** `done`
            - **Description:** Integrate VADER (Valence Aware Dictionary and sEntiment Reasoner) for sentiment analysis of news articles (e.g., using headline + snippet). Store the VADER compound score in `sentiment_score_external` and derive `sentiment_category_derived`. Add a configuration option (e.g., in `backend/app/config.py` or news service) to switch between using VADER sentiment and the sentiment provided directly by the news API (if available, like CoinDesk's). Ensure the system defaults to API-provided sentiment if the switch is off or VADER fails.
        - **Task QL.B3: Create API Endpoint to Serve News**
            - **Status:** `done`
            - **Description:** Create `backend/app/routers/news.py`. Define `NewsArticleRead` Pydantic schema in `backend/app/schemas.py`. Implement `GET /api/news/{symbol}` endpoint to query `news_articles` table for latest N articles for the symbol, order by `published_at` desc. Return `List[NewsArticleRead]`. Register router in `main.py`. **Note: API functional, but data quality dependent on QL.B2.**

   - ### 8.2 Frontend: News Panel UI & Integration
         - **Status:** `done`
         - **Description:** Develop the user interface for displaying the news panel and its content.

         - **Task QL.F1: Design and Implement News Toggle Button & Panel State**
            - **Status:** `done`
            - **Description:** In `frontend/src/views/Home.vue`, add a news toggle button (visible to logged-in users) that controls a `showNewsPanel: false` data property.
        - **Task QL.F2: Create `NewsPanel.vue` Component**
            - **Status:** `done`
            - **Description:** Create `frontend/src/components/NewsPanel.vue`. Conditionally render in `Home.vue` based on `showNewsPanel`. Style as a right sidebar. Include title and close button.
        - **Task QL.F3: Fetch and Display News Articles in `NewsPanel.vue`**
            - **Status:** `done`
            - **Description:** `NewsPanel.vue` accepts `currentChartSymbol` prop. On visible or symbol change, call `GET /api/news/{symbol}`. Display articles: image (`image_url`), clickable headline (`article_url`), source, formatted `published_at`, and sentiment category with visual cue. Handle loading/error states. Resolved display issue by correcting Vuex state property naming in `frontend/src/store/modules/news.js` (ensured `state.newsArticles` was used consistently).
        - **Task QL.F4: Implement Auto-Refresh and "Last Updated" Status for News**
            - **Status:** `done`
            - **Description:** In `NewsPanel.vue`, implement an automatic news refresh mechanism (e.g., every 5-6 minutes) when the panel is visible and a symbol is selected. Ensure the "Last updated" timestamp correctly reflects the time of the latest successful fetch. A manual "Refresh" button also allows immediate re-fetching.

## 9.0 Feature: Perflogs (Performance Logs Backtesting)
   - **Status:** `done`
   - **Description:** Implement a simple backtesting engine that allows registered users to submit trade results and view their overall P&L. This replaces the "My First Watchlist" feature.
   - **Dependencies:** 1.0 (User Accounts)

   ### PL.B Backend Development (Perflogs)
      - **Description:** Create backend infrastructure for `TradeNote` management.

      - **PL.B1: Define `TradeNote` Database Model & Migration**
         - **Status:** `done`
         - **Description:** In `backend/app/models.py`, define `TradeNote` SQLAlchemy model. Fields: `id` (PK), `user_id` (FK to User), `asset_ticker`, `timeframe`, `trade_direction` (ENUM: LONG, SHORT), `entry_price`, `exit_price`, `margin`, `leverage`, `pnl`, `note_text` (max 1000 chars, optional), `created_at`, `updated_at`. Define `TradeDirectionEnum`. Generate and apply Alembic migration to create the `tradenotes` table and `tradedirectionenum` PostgreSQL ENUM type.
         - **Note:** Migration `64cf476d46db` created.

      - **PL.B2: Pydantic Schemas for `TradeNote`**
          - **Status:** `done`
           - **Description:** In `backend/app/schemas.py`, define:
               - `TradeNoteBase` (common fields for creation and reading).
               - `TradeNoteCreate` (for creating new notes, inherits `TradeNoteBase`).
               - `TradeNoteRead` (for reading notes, inherits `TradeNoteBase`, includes `id`, `user_id`, `created_at`, `updated_at`).
               - `TradeDirectionEnum` (Python enum for 'LONG', 'SHORT').
      - **Task PL.B3: Implement CRUD Operations for `TradeNote`**
          - **Status:** `done`
          - **Description:** In `backend/app/crud.py`, implement functions:
              - `create_trade_note(db: Session, trade_note: schemas.TradeNoteCreate, user_id: int)`
              - `get_trade_notes_by_user_and_asset(db: Session, user_id: int, asset_ticker: str)` - Returns all notes for a user and asset, ordered by `created_at` descending.
              - `get_trade_note_by_id(db: Session, trade_note_id: int, user_id: int)` - Fetches a specific note, ensuring it belongs to the user.
              - `delete_trade_note(db: Session, trade_note_id: int, user_id: int)` - Deletes a note, ensuring it belongs to the user.
      - **Task PL.B4: Create API Endpoints for `TradeNote`**
          - **Status:** `done`
          - **Description:** In a new router file (e.g., `backend/app/routers/perflogs.py`):
              - `POST /perflogs/notes/`: Create a new trade note. Requires authentication.
              - `GET /perflogs/notes/{asset_ticker}`: Get all trade notes for the authenticated user and a specific asset ticker.
              - `DELETE /perflogs/notes/{trade_note_id}`: Delete a specific trade note. Requires authentication and ownership.
            Register this router in `backend/app/main.py`.

   ### 9.2 Frontend: Perflogs UI & Integration
      - **Status:** `done`
      - **Description:** Develop the user interface for the Perflogs feature.
      - **UI Mockups:** Refer to `@mockup_perflogs_main_page.png` and `@mockup_perflogs_new_note.png` for UI design inspiration.

      - **Task PL.F1: Create Vuex Module for Perflogs**
          - **Status:** `done`
          - **Description:** Create `frontend/src/store/modules/perflogs.js`.
            State: `tradeNotes: []`, `isLoading: false`, `error: null`, `currentAssetTicker: null`, `currentAssetTimeframe: null`.
            Mutations: `SET_TRADE_NOTES`, `ADD_TRADE_NOTE`, `REMOVE_TRADE_NOTE`, `SET_LOADING`, `SET_ERROR`, `CLEAR_PERFLOGS_DATA`, `SET_CURRENT_ASSET_CONTEXT`.
            Actions:
              - `fetchTradeNotes(assetTicker)`: Calls backend to get notes for an asset.
              - `submitTradeNote(tradeNoteData)`: Calculates PnL, calls backend to create note, then updates state.
              - `deleteTradeNote(tradeNoteId)`: Calls backend to delete note, then updates state.
              - `clearPerflogsData()`: Clears all perflogs related data from the store.
              - `setCurrentAssetContext({ ticker, timeframe })`: Sets the current asset context from the chart.
            Getters: `getTradeNotesSorted`, `getTotalPnl`, `getDateRange`.
      - **Task PL.F2: Implement Main Perflogs Panel Component (`PerflogsPanel.vue`)**
          - **Status:** `done`
          - **Description:** Create `frontend/src/components/PerflogsPanel.vue`.
            - Display overall PnL, "from" and "to" date range (derived from notes).
            - Display a list of `TradeNoteCard.vue` components.
            - Include an "Add note" button.
            - Handle conditional display of "Add note" button vs. `AddTradeNoteForm.vue`.
            - Fetch notes via Vuex action when panel becomes visible or `currentAssetTicker` changes.
            - Provide a close button for the panel.
            - The panel's title should dynamically display the `currentAssetTicker` (e.g., "Perflogs: BTCUSDT").
            - Implement logic to clear Vuex state (`clearPerflogsData`) when the panel is closed.
          - **Dependencies:** PL.F1, PL.F3
      - **Task PL.F3: Implement Trade Note Card Component (`TradeNoteCard.vue`)**
          - **Status:** `done`
          - **Description:** Create `frontend/src/components/TradeNoteCard.vue` to display individual trade notes.
            - Show asset, timeframe, direction, entry, exit, margin, leverage, PnL for the trade, and creation date.
            - Display "Note" text (first 50 chars with "read more" if longer, expandable).
            - Include a delete button (trash icon) that dispatches Vuex action to delete the note.
          - **Dependencies:** PL.F1
      - **Task PL.F4: Implement Add Trade Note Form Component (`AddTradeNoteForm.vue`)**
          - **Status:** `done`
          - **Description:** Create `frontend/src/components/AddTradeNoteForm.vue`.
            - Form fields for: `trade_direction` (select: Long/Short), `entry_price`, `exit_price`, `margin`, `leverage`, `note_text` (textarea).
            - `asset_ticker` and `timeframe` should be auto-filled from Vuex state (chart context).
            - Implement client-side PnL calculation before submission:
                - Long: `pnl = ((exit_price / entry_price) - 1) * margin * leverage`
                - Short: `pnl = (1 - (exit_price / entry_price)) * margin * leverage`
                - (Leverage defaults to 1 if not provided or invalid).
            - Implement character limit (1000 symbols) for `note_text` with UI feedback (error message, disabled submit button).
            - Submit button calls Vuex action to save the note.
            - Close button ("x") discards form data and hides the form, showing "Add note" button again.
          - **Dependencies:** PL.F1
      - **Task PL.F5: Integrate Perflogs into `Home.vue`**
          - **Status:** `done`
          - **Description:**
            - Add a "Perflogs" button in `Home.vue` (e.g., to the left of "News" button), visible only to authenticated users.
            - Toggle visibility of `PerflogsPanel.vue`.
            - When Perflogs panel is opened, dispatch Vuex action to set `currentAssetTicker` and `currentAssetTimeframe` based on the chart's current live context (`lastLiveAsset`, `lastLiveTimeframe` from `chart` module). If no live context, Perflogs might show a message or disable "Add note".
          - **Dependencies:** PL.F1, PL.F2

   ### 9.3 Styling and Refinements
      - **Status:** `done`
      - **Description:** Apply consistent styling and refine user experience.
      - **UI Mockups:** Refer to `@mockup_perflogs_main_page.png` and `@mockup_perflogs_new_note.png` for UI design inspiration.

      - **Task PL.S1: Apply Styling to Perflogs Components**
          - **Status:** `done`
          - **Description:** Style `PerflogsPanel.vue`, `TradeNoteCard.vue`, and `AddTradeNoteForm.vue` according to mockups and project's overall design language. Ensure responsive behavior if applicable.
      - **Task PL.S2: Implement Smooth Transitions for Add Note Form**
          - **Status:** `done`
          - **Description:** Implement smooth show/hide transitions (e.g., fade, slide) when switching between "Add note" button and `AddTradeNoteForm.vue`.

## 10.0 Final Testing & Documentation Update (Post-Perflogs)
   - **Status:** `to_do`
   - **Description:** Conduct final testing of the Perflogs feature and update all relevant project documentation.
   - **Dependencies:** 9.0

   ### 10.1 Comprehensive Testing of Perflogs
      - **Status:** `to_do`
      - **Description:**
         - Test backend API endpoints for `TradeNote` CRUD operations.
         - Test frontend functionality: adding notes, PnL calculation (overall and per trade), display of notes, date ranges, deletion, text note character limit, "read more" functionality.
         - Test behavior when switching assets on the chart.
         - Test UI responsiveness and transitions.
   ### 10.2 Update Project Documentation
      - **Status:** `to_do`
      - **Description:** Update `DOCUMENTATION.md`, `DIARY.md`, and `CHANGELOG.md` to reflect the implementation of the Perflogs feature, its architecture, API endpoints, and frontend components.

## 11.0 Interactive Asset/Timeframe Selector & Data Context Management
   - **Status:** `done`
   - **Description:** Make asset and timeframe selectors interactive. Changes to asset/timeframe should correctly clear and reload chart data. Contextual updates for News/Perflogs panels (News/Perflogs should only refetch if asset changes, not just timeframe). Add a conditional "Log in" button and update general UI layout of the top bar in `Home.vue`. Update browser tab title.
   - **Dependencies:** 6.4, 8.2, 9.2

   ### 11.1 Backend Endpoint for Available Timeframes
      - **Status:** `done`
      - **Description:** Create endpoint `/api/config/proactive-timeframes` to return `PROACTIVE_TIMEFRAMES_LIST` from `app.config`.
   ### 11.2 Frontend: Editable Asset Name in Selector
      - **Status:** `done`
      - **Description:** `AssetTimeframeSelector.vue` allows asset name editing on double-click, emits `asset-updated`.
   ### 11.3 Frontend: Selectable Timeframe in Selector
      - **Status:** `done`
      - **Description:** `AssetTimeframeSelector.vue` provides a dropdown for timeframes (fetched from backend via `Home.vue`), emits `timeframe-updated`.
   ### 11.4 Frontend: Data Clearing & Context Update Logic
      - **Status:** `done`
      - **Description:** Vuex (`chart.js`) updated with state/mutations/actions for `currentDisplayAsset` and `currentDisplayTimeframeUserSelected`. `Home.vue` uses these for `AssetTimeframeSelector`, handles update events, and watches a `currentContextIdentifier` to trigger `handleAssetOrTimeframeChange`. This method now correctly clears chart data (for both modes), reloads live chart data, and conditionally clears News/Perflogs data (only if asset changes). Add conditional "Log in" button. Refine `Home.vue` top bar layout. Update browser tab title.
   ### 11.5 Frontend: Global Asset/Timeframe State (Vuex) - Merged/Covered
      - **Status:** `done`
      - **Description:** Ensured that the `currentDisplayAsset` and `currentDisplayTimeframeUserSelected` in Vuex (`chart.js` module) serve as the global source of truth for what the user has selected in the UI. `Home.vue` and its child components (like `AssetTimeframeSelector`, `NewsPanel`, `PerflogsPanel`) now primarily read from or update this centralized Vuex state. This was largely addressed as part of Task 11.4.

## 12.0 Real-time Current Candle Updates (Live Ticks)
   - **Status:** `done`
   - **Description:** Modify the data ingestion service and frontend to process and display real-time price ticks, updating the current (unclosed) candle dynamically, similar to how Binance charts behave.
   - **Dependencies:** 6.0 (Live Price Data Integration)

   ### 12.1 Backend: Real-time Tick Processing for Current Candle
      - **Status:** `done`
      - **Description:** Enhance the data ingestion service to handle live price ticks.
      - **12.1.1 Research Binance WebSocket Streams for Live Ticks:**
         - **Status:** `done`
         - **Description:** Identify the most suitable Binance WebSocket stream for real-time price updates that affect the current candle (e.g., Aggregate Trade Streams (`<symbol>@aggTrade`) or Kline streams with frequent unclosed updates).
      - **12.1.2 Modify/Extend `BinanceWebSocketManager` for Tick Streams:**
         - **Status:** `done`
         - **Description:** Adapt `BinanceWebSocketManager` (or create a new, similar manager) to connect to the chosen tick stream (from 12.1.1) for each proactive symbol. Update message parsing for the tick stream's payload (e.g., price, quantity, timestamp of the trade). (Refined to mean modifying `_parse_kline_message` to pass unclosed klines from existing stream).
      - **12.1.3 Implement `live_tick_processor` in Data Ingestion Service:**
         - **Status:** `done`
         - **Description:** Create a new function `live_tick_processor` in `backend/data_ingestion_service/main.py`. This function will receive individual price ticks. It will need to determine which kline (based on current timeframe and tick timestamp) this tick belongs to. (Refined: merged into `kline_data_processor`).
      - **12.1.4 Logic to Update Current (Unclosed) Kline Data:**
         - **Status:** `done`
         - **Description:** The `live_tick_processor` will construct an "updated current kline" object. For a given tick and timeframe: Determine the current kline's `open_time`. The `open` price remains the open price of the current interval. `high` is `max(current_kline.high, tick.price)`. `low` is `min(current_kline.low, tick.price)`. `close` is `tick.price`. `volume` is `current_kline.volume + tick.quantity`. `is_closed` will be `false`. (Implemented in `kline_data_processor` for unclosed klines).
      - **12.1.5 Redis Pub/Sub for Live Tick Updates:**
         - **Status:** `done`
         - **Description:** Publish the "updated current kline" object (from 12.1.4) via Redis Pub/Sub. This could be a new channel (e.g., `kline_tick_updates:<symbol>:<timeframe>`) or the existing `kline_updates:...` channel but with a message type flag. (Implemented: uses existing channel with type `kline_tick`).
      - **12.1.6 Integration into Ingestion Service Main Loop:**
         - **Status:** `done`
         - **Description:** The main ingestion service (`backend/data_ingestion_service/main.py`) will launch and manage these new tick stream connections and processors alongside existing kline stream connections. (Verified: no changes needed in main loop structure).

   ### 12.2 Frontend: Displaying Real-time Tick Updates on Current Candle
      - **Status:** `done`
      - **Description:** Update the frontend to consume and display these live tick updates.
      - **12.2.1 Modify Frontend WebSocket Handler for Tick Updates:**
         - **Status:** `done`
         - **Description:** Update WebSocket logic in `frontend/src/views/Home.vue` to listen for the new live tick messages (from 12.1.5). Differentiate these from regular closed kline messages. (Backend part required no changes, frontend part is done).
      - **12.2.2 Vuex Action/Mutation for Live Tick Update:**
         - **Status:** `done`
         - **Description:** Create new Vuex actions/mutations in `frontend/src/store/modules/chart.js` (e.g., `PROCESS_LIVE_KLINE_TICK`).
      - **12.2.3 `DataCube` Update Logic for Live Tick:**
         - **Status:** `done`
         - **Description:** The Vuex mutation will update the `DataCube`. If the incoming tick's kline `open_time` matches the `open_time` of the last kline in `DataCube.ohlcv`, update that last kline's HLCV values. If the incoming tick's kline `open_time` is newer than the last kline in `DataCube.ohlcv`, append it as a new candle to `DataCube.ohlcv`. This ensures the last candle on the chart is either being updated or a new one is being formed.
      - **12.2.4 Chart Reactivity and Performance:**
         - **Status:** `to_do`
         - **Description:** Ensure `trading-vue-js` reacts to the modification of the last OHLCV array element (or the addition of a new one) and updates the display smoothly. Monitor performance.

### PL.D: Perflogs Documentation & Deployment (Future)