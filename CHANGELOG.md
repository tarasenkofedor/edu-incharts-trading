# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Detailed planning for "Quick Look" News Panel feature (Task 8.0 in `TASKS.md`) including:
    - Backend: `NewsArticle` DB model (with `image_url`), `marketaux` polling service, API endpoint.
    - Frontend: News toggle, `NewsPanel.vue` component for displaying articles with images and sentiment.
- Initial project setup for new iteration.
- `DIARY.md` created for AI action logging.
- `TASKS.md` created, based on `PREV_TASKS.md` with reset statuses and updated requirements (user schema, local frontend charting).
- `backend/requirements.txt` created with initial dependencies.
- `frontend/` directory structured for local `trading-vue-js` components (`frontend/src`, `frontend/dist`, `frontend/docs` organized by user).
- Rule added to `project_guidelines/PROJECT_RULES.md` for backend Python execution via `backend/.venv`.
- This `CHANGELOG.md` file created.
- **Task 1.1:** Initial FastAPI backend project structure:
    - `backend/app/__init__.py` created.
    - `backend/app/main.py` with FastAPI app and `/ping` health check endpoint created.
    - `backend/.gitignore` created.
    - `VERSION_COUNTER.txt` and `VERSION` files created.
- **News Feature (Task 8.0 - In Progress):**
    - Backend: `NewsArticle` DB model, Alembic migration (`941c73ffbd8c`), `news_fetcher_service` for Marketaux polling, `/api/news/{symbol}` endpoint.
    - Frontend: "News" toggle button in `Home.vue`, `NewsPanel.vue` component, Vuex `news` module (`frontend/src/store/modules/news.js`) for state management.
- **Perflogs Feature (Task 9.0 - Backend Foundation):**
    - Defined `TradeDirectionEnum` and `TradeNote` SQLAlchemy model in `backend/app/models.py`.
    - Generated and applied Alembic migration `64cf476d46db` to create the `tradenotes` table and `tradedirectionenum` PostgreSQL ENUM type.
- **Perflogs Feature (Task 9.0 - Pydantic Schemas):**
    - Defined `TradeNoteBase`, `TradeNoteCreate`, and `TradeNoteRead` Pydantic schemas in `backend/app/schemas.py`.
    - Configured JSON encoders for `Decimal` to `float` and `datetime` to integer millisecond timestamps.
- **Perflogs Feature (Task 9.0 - CRUD Operations):**
    - Implemented CRUD functions (`create_trade_note`, `get_trade_notes_by_user_and_asset`, `get_trade_note_by_id`, `delete_trade_note`) for `TradeNote` in `backend/app/crud.py`.
- **Perflogs Feature (Task 9.0 - API Endpoints):**
    - Created `backend/app/routers/perflogs.py` with API endpoints for `TradeNote` (POST `/notes/`, GET `/notes/{asset_ticker}`, DELETE `/notes/{trade_note_id}`).
    - Registered the `perflogs` router in `backend/app/main.py`.
- **Perflogs Feature (Task 9.0 - Frontend Vuex Module):**
    - Created `frontend/src/store/modules/perflogs.js` with state, mutations, actions (for CRUD and context), and getters.
    - Registered the `perflogs` module in the main Vuex store (`frontend/src/store/index.js`).
- **Perflogs Feature (Task 9.0 - Frontend Panel Component):**
    - Created `frontend/src/components/PerflogsPanel.vue` with basic structure, Vuex integration for displaying summary data (P&L, date range), loading/error states, and placeholders for note cards and the add note form. Includes initial styling.
- **Perflogs Feature (Task 9.0 - Frontend Trade Note Card Component):**
    - Created `frontend/src/components/TradeNoteCard.vue` to display individual trade note details (asset, P&L, dates, etc.) with a delete button and expandable note text. Includes styling.
    - Integrated `TradeNoteCard.vue` into `PerflogsPanel.vue` to list notes.

### Changed
- `CHANGELOG.md` corrected to remove unrelated historical entries.
- Backend Python execution rule added to `project_guidelines/PROJECT_RULES.md`.

### Added
- **Task 1.2:** Database setup (PostgreSQL & Alembic):
    - `backend/app/models.py` with `User` model and `SubscriptionPlanEnum`.
    - `backend/app/schemas.py` with Pydantic models for User and Token.
    - `backend/app/config.py` for Pydantic settings (loading from `.env`).
    - `backend/app/database.py` for SQLAlchemy engine and session management.
    - Alembic initialized and configured in `backend/`.
    - Initial migration for `users` table generated and applied.

- **Task 1.3:** User Registration Endpoint:
    - `backend/app/security.py` with password hashing and JWT creation.
    - `backend/app/crud.py` with initial User CRUD functions.
    - `backend/app/routers/auth.py` with `/auth/register` endpoint.
    - `backend/app/routers/__init__.py` created.
    - `auth` router included in `backend/app/main.py`.

- **Task 1.4:** User Login Endpoint:
    - Added `/auth/login` endpoint to `backend/app/routers/auth.py` for JWT-based authentication.

- **Task 1.5:** JWT Authentication Middleware & Dependencies:
    - `OAuth2PasswordBearer` scheme and `get_current_user`, `get_current_active_user` dependencies added to `backend/app/security.py`.
    - `backend/app/routers/users.py` created with protected `/users/me` endpoint.
    - `users` router included in `backend/app/main.py`.

Parent **Task 1.0 (Foundational Setup & User Accounts)** completed.

### Changed
- `CHANGELOG.md` corrected to remove unrelated historical entries.
- Backend Python execution rule added to `project_guidelines/PROJECT_RULES.md`.

### Fixed
- **Backend Core:** Resolved critical database migration issue that prevented `users` table creation. Addressed complex ENUM type (`subscriptionplanenum`) handling within Alembic migrations for PostgreSQL, ensuring the table is now created correctly.
- **Backend Routing:** Fixed 404 errors for `/auth/register` and `/users/me` API endpoints by correcting misconfigured routing prefixes in `backend/app/routers/auth.py` and `backend/app/routers/users.py` respectively.
- **Frontend Charting:** Resolved an issue where the initial chart display and subsequent display of uploaded CSV data were not working correctly. Fixes involved `DataCube` initialization logic in `dc_core.js` and the `decubed` computed property in `TradingVue.vue` to ensure correct data propagation to `Chart.vue`.
- **Frontend Charting:** Corrected timestamp parsing in the backend (`/data/upload_csv`) to interpret numeric timestamps from CSVs as milliseconds (`unit='ms'`), fixing incorrect date displays on the chart.
- **Frontend Charting:** Optimized chart crosshair performance by throttling mouse move event handling (`updater.sync`) using `requestAnimationFrame`. This significantly reduced lag when moving the cursor quickly over the chart.
- **Frontend Charting:** Fixed a `TypeError: Cannot read properties of undefined (reading 'measureText')` that occurred on initial chart load by removing `immediate: true` from the `data` watcher in `Chart.vue`, ensuring `this.ctx` (canvas context) is initialized before layout calculations that depend on it.
- **Frontend Uploader:** Resolved ESLint errors (formatting and `no-async-promise-executor`) in `frontend/src/components/SignalUpload.vue`.
- **Frontend Uploader:** Fixed a bug in `frontend/src/components/SignalUpload.vue` where valid signal CSV files were incorrectly parsed as having only one line due to incorrect newline splitting. Changed `fileText.split(/\r?\n/)` to `fileText.split('\n')` in `parseSignalCsv` method.
- **Frontend Charting (Live Mode Signals):**
    - Refactored `ADD_SIGNALS` Vuex mutation in `frontend/src/store/modules/chart.js` to correctly and consistently target `DataCube.data.onchart` for adding new signal overlays. This resolves a warning about using fallback paths and ensures signals are added to the array `trading-vue-js`'s `DataCube` internally uses.
    - In `frontend/src/views/Home.vue`, when handling signal uploads in live mode:
        - Incremented `chartResetKey` after adding signals to force a re-mount of the `TradingVue` component.
        - Maintained logic to capture the visible chart range before adding signals and attempt to restore it using `setRange()` in `$nextTick` after the chart re-mounts. This aims to preserve the user's viewport.
    - These changes address issues where signals might appear briefly and disappear or cause the chart to zoom out unexpectedly when uploaded in live mode.
- **Frontend Charting (Signal Persistence):**
    - Corrected `SET_LIVE_CHART_DATA` and `PREPEND_HISTORICAL_KLINES` Vuex mutations in `frontend/src/store/modules/chart.js` to accurately preserve existing `onchart` and `offchart` overlays. These mutations now read overlays from the correct `state.chartDataCube.data.onchart` (and `.offchart`) path of the current `DataCube` before creating a new `DataCube` instance with updated kline data. This ensures that user-uploaded signals persist through historical data loads and live updates in "Live Chart" mode.
- **Frontend Charting (`Trades.vue`):** Significantly improved rendering performance of signal overlays by implementing horizontal culling (drawing only markers within the visible canvas width) and zoom-dependent label rendering (drawing labels only when candle width `layout.px_step` exceeds a threshold). This addresses lag during panning and zooming with many signals.
- **Frontend News Display:** Resolved a critical issue in `frontend/src/store/modules/news.js` where the `NewsPanel.vue` component would show "No news available" even when data was fetched. The `state` object was using `articles` as the property name for storing news items, while the mutations (`SET_NEWS_ARTICLES`, `CLEAR_NEWS`) and the component's `mapState` were expecting `newsArticles`. Corrected the state property name to `newsArticles` and updated the corresponding getter to ensure reactive data flow and correct display of news articles.

## [v5] - 2025-05-19
### Added
- Initial `docker-compose.yml` setup.
- Redis service (`inchart_redis`) configured to run in Docker with data persistence.
- TimescaleDB service (`inchart_postgres_timescaledb`) configured to run in Docker with data persistence and specified credentials. Host port mapped to 5433 to avoid conflicts.

### Changed
- Development environment for Redis and TimescaleDB now utilizes Docker containers.

## [v14] - 2025-05-20 (Frontend Live Mode - Initial Setup)

### Added
- **Frontend (`Home.vue` & Vuex `chart.js`):**
    - Implemented "Live" / "Custom" chart mode switcher UI in `Home.vue`.
    - Uploaders (`CsvUpload`, `SignalUpload`) are now conditionally displayed based on `chartMode`.
    - Vuex store (`chart.js`) now manages `chartMode`, `lastLiveAsset`, `lastLiveTimeframe`.
    - Default chart mode is "custom", loading mock data.
    - Switching to "custom" mode resets chart to mock data.
    - Switching to "live" mode clears the chart and then triggers an initial fetch of historical klines for the default asset/timeframe (e.g., BTCUSDT, 1m, ~300 klines) from the backend API (`/data/klines/...`).
    - Loaded historical klines are displayed on the chart.
    - API backfill status is logged to the console.

### Changed
- Vuex `chart.js` state initialization and actions/mutations refactored to support distinct data handling for "live" and "custom" modes.
- `Home.vue` structure updated for new mode controls and conditional uploader visibility.

## [v15] - 2025-05-20 (Frontend Live Mode - Paginated History)

### Added
- **Frontend (`Home.vue` & Vuex `chart.js`):**
    - Implemented paginated loading of older historical kline data in "Live" mode.
    - When the user pans the chart to the left, approaching the oldest data currently loaded, an API call is made to fetch an even older batch of klines.
    - Fetched older klines are prepended to the existing chart data.
    - `oldestKlineTimestampLoaded` state is maintained in `Home.vue` to track the current historical data boundary.
    - `TradingVue`'s `@range-changed` event is used to trigger checks for loading more history.
    - New Vuex actions/mutations (`prependHistoricalKlines`, `PREPEND_HISTORICAL_KLINES`) added to support prepending data to the `DataCube`.
    - The asset/timeframe display in the UI now dynamically reflects `lastLiveAsset` and `lastLiveTimeframe` when in "Live" mode.

### Changed
- Modified `fetchInitialHistoricalKlines` in `Home.vue` to also manage `isLoadingMoreHistory` and `oldestKlineTimestampLoaded` states.

## [v19] - 2025-05-20
### Added
- **Frontend Live Data Integration (Task 6.4):**
    - Implemented "Live" / "Custom" chart mode switcher in `Home.vue` with conditional visibility for OHLCV (custom) and Signal (live) uploaders. (Task 6.4.2)
    - Vuex store (`chart.js`) updated to manage `chartMode`, `lastLiveAsset`, `lastLiveTimeframe`. Mode switching clears/resets chart data appropriately. (Tasks 6.4.1, 6.4.3)
    - Implemented initial historical kline data loading (~300 klines) from `/data/klines/...` when switching to "Live" mode. (Task 6.4.4 - Part 1)
    - Implemented paginated loading of older historical klines when panning left in "Live" mode, using `@range-changed` event and fetching from API with `end_ms`. (Task 6.4.4 - Part 2)
    - Implemented WebSocket connection in `Home.vue` to backend `/ws/klines/...` for live kline updates. Vuex action `updateLiveKline` processes incoming messages. (Task 6.4.5)
    - Ensured signal overlays persist correctly when loading live historical data and during live updates by modifying `SET_LIVE_CHART_DATA` Vuex mutation. (Task 6.4.6)
    - Added UI indicators in `Home.vue` for initial data loading, historical data loading, and backend data backfill status. (Task 6.4.7)

### Changed
- Vuex `chart.js` refactored to support distinct data handling and state for "live" and "custom" chart modes.
- `Home.vue` significantly updated to manage mode switching, historical data fetching, WebSocket connections, and UI feedback for live data operations.

### Fixed
- Ensured `SET_LIVE_CHART_DATA` mutation in `chart.js` preserves existing onchart/offchart overlays so signals are not lost when live historical data is loaded.

## [v20] - 2025-05-21
- Clarified Docker usage (Redis, TimescaleDB).
- Confirmed initial data population strategy for TimescaleDB via Data Ingestion Service (historical backfill).
- Added new frontend task `6.4.8 Frontend UX: Initial Data Preload Window / No Data Pop-up` to `TASKS.md` for better UX during initial data loading for live charts.
- Continued work on backend tests (Task 6.5.1), with `test_get_klines_with_data_from_db` passing after resolving schema, timezone, and API path issues.

### [v21] - 2025-05-21
- **Backend Testing (Task 6.5.1):**
    - Implemented API tests for `/data/klines/{symbol:path}/{timeframe}` covering Redis cache interactions (data only in Redis, Redis + DB, backfill status reporting).
    - Created `test_websocket_api.py` and implemented initial tests for `/ws/klines/{symbol:path}/{timeframe}` WebSocket endpoint, including happy path (connection, subscription, message relay) and Redis connection failure scenarios.
    - Updated `TASKS.md` to reflect progress on API testing for live data features.

### [v22] - 2025-05-21
- **Task Status Correction:** Corrected `TASKS.md` to reflect prior completion of live data integration tasks (6.0-6.4 and sub-tasks). Testing/documentation tasks renumbered (e.g., 6.5 became 7.0).
- **Backend Testing (Task 7.1 - formerly 6.5.1):**
    - Completed unit and integration tests for the Data Ingestion Service components:
        - `BinanceWebSocketManager`: Tested connection, message handling, reconnection, and shutdown.
        - `historical_data_fetcher`: Tested API interaction, pagination, rate limit retries, and error handling for kline fetching; mocked DB save tests.
        - `kline_data_processor`: Tested the pipeline for DB persistence, Redis caching, and Redis Pub/Sub, including error handling at each stage.
    - Task 7.1 (Backend Unit & Integration Tests) is now fully complete.
- **Frontend UX (Task 6.4.8):**
    - Implemented `ChartStatusPopup.vue` for bottom-left notifications.
    - Integrated into `Home.vue` to display messages regarding live data loading, backfill status, and WebSocket connection states.

## [Unreleased] - YYYY-MM-DD
### Added
- Placeholder for future changes

## [v0.1.5] - 2025-05-21
### Fixed
- Corrected `news.router` prefix in `backend/app/main.py` to resolve 404 errors for the news API.
- Added `MARKETAUX_API_TOKEN` to Pydantic `Settings` in `backend/app/config.py` to allow news fetcher service to load API key.

### Changed
- Refactored `NewsPanel.vue` to use a new Vuex module (`store/modules/news.js`) for state management (articles, loading, error).
- News articles are now cleared from the store when the `NewsPanel` is closed, ensuring fresh data is loaded when switching symbols or reopening.
- Article images in `NewsPanel.vue` are now clickable hyperlinks to the original article.

### Improved
- News fetching logic in `news_fetcher_service/main.py` reviewed against Marketaux API for correct field parsing (snippet, published_at, sentiment) and recency.

### Fixed
- **News Feature (Backend - API):** Corrected a router prefix issue in `backend/app/main.py` for the news API (`news.router`). The router prefix for news was `/api/news`, and it was being included with an additional `/api` prefix, resulting in `/api/api/news/...` and 404 errors. Removed the redundant prefix from `main.py`.
- **News Feature (Backend - Service):** Added `MARKETAUX_API_TOKEN: str` to the Pydantic `Settings` model in `backend/app/config.py`. This allows the `news_fetcher_service` to correctly load the API token from environment variables, resolving an `AttributeError`.
- **News Feature (Frontend - Display):** Resolved an issue where `NewsPanel.vue` would show "No news available" despite data being fetched. Corrected Vuex `news` module state property name from `articles` to `newsArticles` and updated the getter for consistent reactive updates to the component.
- **News Feature (Backend - Data Quality):** Identified that the `news_fetcher_service/main.py` is currently fetching old/irrelevant news. Added `sort=published_on` to the Marketaux API call parameters in `news_fetcher_service/main.py` to attempt to retrieve most recent articles. **Further investigation needed for full data quality resolution.**

## [0.1.23] - YYYY-MM-DD
### Added
- **Perflogs Feature (Backend):**
  - `TradeDirectionEnum` (`backend/app/models.py`)
  - `TradeNote` SQLAlchemy model (`backend/app/models.py`)
  - Alembic migration `64cf476d46db` for `tradenotes` table and `tradedirectionenum`.
  - Pydantic schemas `TradeNoteBase`, `TradeNoteCreate`, `TradeNoteRead` (`backend/app/schemas.py`).
  - CRUD operations for trade notes (`backend/app/crud.py`).
  - API endpoints for trade notes (`POST /perflogs/notes/`, `GET /perflogs/notes/{asset_ticker}`, `DELETE /perflogs/notes/{trade_note_id}`) in `backend/app/routers/perflogs.py`.
  - Registered `perflogs` router in `backend/app/main.py`.
- **Perflogs Feature (Frontend):**
  - Vuex module `perflogs.js` for state management (`frontend/src/store/modules/perflogs.js`).
  - `PerflogsPanel.vue` component: Main sidebar panel to display trade notes and summary (`frontend/src/components/PerflogsPanel.vue`).
  - `TradeNoteCard.vue` component: Displays individual trade note details (`frontend/src/components/TradeNoteCard.vue`).
  - `AddTradeNoteForm.vue` component: Form for adding new trade notes (`frontend/src/components/AddTradeNoteForm.vue`).
  - Integrated `PerflogsPanel.vue` into `Home.vue`, including a toggle button and passing of asset context.

### Changed
- Updated `VERSION` to `0.1.23` and `VERSION_COUNTER.txt` to `23`.
- Corrected `leverage: Decimal = Field(..., ge=1.0, default=1.0)` to `leverage: Decimal = Field(default=1.0, ge=1.0)` in `TradeNoteBase` schema (`backend/app/schemas.py`).

### Fixed
- Resolved `TypeError: Field() got multiple values for argument 'default'` in `backend/app/schemas.py`.

### Removed
- Nothing in this version.

## [0.1.24] - 2025-05-23
### Added
- **Perflogs Feature (Frontend - UI/UX Refinements):**
  - Added Font Awesome 5 CDN link to `frontend/public/index.html` to ensure icons (delete, close) are displayed correctly.
  - Styled the "No trade notes recorded for this asset yet." message in `PerflogsPanel.vue` with an orange warning theme.

### Changed
- **Perflogs Feature (Frontend Styling & Behavior):**
  - `PerflogsPanel.vue`:
    - Close button styled as a white 'X'.
    - Summary P&L section now has rounded corners and a border consistent with trade note cards.
    - Ensured consistent width for summary section, "Add Note" button, and trade note cards within the panel.
    - Improved data clearing logic: Perflogs data is now reliably cleared and the "Add Note" form hidden when the panel is closed, opened with an N/A ticker, or the asset context changes.
    - "Add Note" button is correctly disabled when `assetTicker` is 'N/A' or data is loading.
    - Total P&L of zero is now displayed neutrally (e.g., "0.00 USD") without a '+' sign.
  - `TradeNoteCard.vue`:
    - Delete icon background is transparent, turning red on hover for better visual feedback.
- Updated `VERSION` to `0.1.24` and `VERSION_COUNTER.txt` to `24`.

### Fixed
- Icons (trash can, panel close) not appearing in the Perflogs feature due to missing Font Awesome integration. This is now resolved.

## [0.1.25] - YYYY-MM-DD // TODO: Replace with current date
### Changed
- **News Panel (Frontend Behavior & Styling):**
  - `frontend/src/views/Home.vue` now dispatches `news/clearNews` Vuex action when switching between "Live" and "Custom" chart modes. This ensures news articles related to a previous asset or mode are cleared.
  - `frontend/src/components/NewsPanel.vue` has been re-styled with a dark theme to match the `PerflogsPanel.vue` for visual consistency. This includes updates to background colors, text colors, borders, button styles, sentiment tag appearance, and scrollbar styles.

### Fixed
- Minor linter/spacing issues in `frontend/src/components/NewsPanel.vue` styles.

## [0.0.8] - 2025-05-24

### Fixed
*   Resolved issue where chart data was cleared but new data failed to load when changing asset or timeframe. Ensured `fetchInitialHistoricalKlines` is correctly called with the new context in `Home.vue`.
*   News and Perflogs panels in `Home.vue` no longer refetch data when only the timeframe is changed; they now only update if the selected asset changes.
*   Corrected ESLint `no-unused-vars` error in the `chart.js` Vuex module by removing an unused `changed` variable in the `setLastLiveAssetAndTimeframe` action.

### Added
*   Added a "Log in" button to the top navigation bar in `Home.vue`, visible only when the user is not authenticated. This button is styled with a blue theme.
*   Applied new styling (greyish background, hover effect) to the "Home" link in the top navigation of `Home.vue`.

### Changed
*   Updated the browser tab title for the application to "InCharts" (modified `frontend/public/index.html`).
*   Restructured the top navigation bar in `Home.vue` into a two-section layout:
    *   Left section (`mode-asset-controls`): "Home" link, `AssetTimeframeSelector`, "Live Chart"/"Custom Chart" mode buttons.
    *   Right section (`user-controls`): "News" toggle, "Perflogs" toggle, user greeting, "Log out" button (original red styling restored), and the new conditional "Log in" button.
*   Updated `DOCUMENTATION.md` to reflect recent UI layout changes in `Home.vue`, the addition of the "Log in" button, and the browser tab title modification.

## [0.0.9] - 2025-05-24
### Added
- **Real-time Current Candle Updates (Live Ticks) (Task 12.0):**
  - **Backend (Data Ingestion Service & API - Task 12.1):**
    - Modified `BinanceWebSocketManager` (`backend/data_ingestion_service/binance_connector.py`) to parse and pass kline data regardless of whether it's a closed candle (`k.x: true`) or an update to an unclosed candle (`k.x: false`). The `is_closed` status is now included in the processed data.
    - Updated `kline_data_processor` (`backend/data_ingestion_service/main.py`):
      - For closed klines: Continues to save to TimescaleDB, update Redis cache, and publish to Redis Pub/Sub (`kline_updates:<symbol>:<timeframe>`) with `type: "kline_closed"`. Corrected Redis ZSET trimming logic to keep the newest `MAX_KLINES_IN_REDIS` entries.
      - For unclosed kline ticks: Constructs a kline object representing the forming candle and publishes it to the same Redis Pub/Sub channel (`kline_updates:<symbol>:<timeframe>`) but with `type: "kline_tick"`.
    - Confirmed backend WebSocket API (`/ws/klines/{symbol}/{timeframe}`) requires no changes as it already relays raw JSON from Pub/Sub, now correctly passing messages with the new `type` field.
  - **Frontend (Vuex & Chart Display - Task 12.2):**
    - Added `PROCESS_LIVE_KLINE_TICK` mutation and `processLiveKlineTick` action to `frontend/src/store/modules/chart.js`. This logic updates the `liveChartDataCube` by modifying the last kline or appending a new one for incoming ticks, ensuring reactivity and preserving overlays.
    - Updated the `livePriceSocket.onmessage` handler in `frontend/src/views/Home.vue` to differentiate between `kline_closed` and `kline_tick` message types from the WebSocket and dispatch the appropriate Vuex action.

### Changed
- Updated `VERSION` to `0.0.9` and `VERSION_COUNTER.txt` to `26` (assuming previous was 25, will verify).

### Fixed
- ESLint errors in `backend/data_ingestion_service/binance_connector.py`, `backend/data_ingestion_service/main.py`, `frontend/src/store/modules/chart.js`, and `frontend/src/views/Home.vue` related to the live tick implementation.
