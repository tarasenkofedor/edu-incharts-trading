# InChart �� - Trading Charting & Analysis Platform MVP

**Version: 0.0.9** (as of 2025-05-24)

InChart is a Minimum Viable Product (MVP) for a trading analysis platform. It allows users to visualize financial market data, upload custom OHLCV (Open, High, Low, Close, Volume) and trading signal data, connect to live Binance price feeds, view market news, and track trade performance through a "Perflogs" feature.

A key characteristic of this project is its use of a **local, "raw" version of the `trading-vue-js` library** (Vue 2 compatible) for its charting capabilities. This approach allows for deep customization and control over the charting components, bypassing reliance on external package managers for this core library.

## ✨ Overview

The primary goal of InChart is to offer a flexible and extensible charting tool. It caters to users who want to analyze market data using standard candlestick charts, as well as those who wish to import and visualize their own datasets and custom trading signals. The platform aims to provide a foundation for more advanced technical analysis and backtesting features in the future. It is built with a modern technology stack, prioritizing asynchronous operations, data integrity, and a clean, intuitive user interface.

## 🚀 Core Features

*   **User Authentication & Management:**
    *   Secure user registration (nickname, email, password) and login (JWT-based).
    *   Password hashing using `bcrypt`.
    *   Protected endpoints for user-specific data.
    *   PostgreSQL `User` model with basic profile information and subscription plan fields (currently for future use).

*   **Advanced Charting (via local `trading-vue-js`):**
    *   Display of OHLCV candlestick charts with interactive zooming and panning.
    *   Performance-optimized crosshair for data inspection.
    *   **Real-time Current Candle Updates (Live Ticks):** In "Live" mode, the currently forming candle updates dynamically with incoming price ticks from Binance, providing a near real-time view.
    *   Optimized rendering for signal overlays (`Trades.vue`) with:
        *   **Horizontal Culling:** Only signals within the visible chart area are rendered.
        *   **Zoom-Dependent Label Visibility:** Signal labels are only displayed at appropriate zoom levels to prevent clutter.

*   **Custom Data Upload & Display:**
    *   **OHLCV Data:** Users can upload custom price data in CSV format (`timestamp,open,high,low,close,volume`). Client-side and backend validation ensures data integrity.
    *   **Signal Data:** Users can upload custom trading signals (e.g., buy/sell markers, indicators) in CSV format (`timestamp,type,price,label,color,icon`). These are parsed and displayed as customizable "Trades" overlays on the chart.

*   **Live Price Data Integration (Binance):**
    *   **Robust Data Ingestion Service:** A standalone background worker (`backend/data_ingestion_service/`) connects to Binance WebSocket streams for live kline data (e.g., BTCUSDT 1m), handling both closed klines and unclosed kline "tick" updates.
    *   **Historical Data Backfill & Gap Filling:** The service automatically backfills historical kline data from the Binance REST API on startup for configured symbols/timeframes and intelligently fills any detected gaps.
    *   **Efficient Data Persistence & Caching:**
        *   Live and historical klines are stored in a TimescaleDB hypertable for efficient time-series data management.
        *   Recent klines are cached in Redis (sorted sets) for fast API retrieval.
        *   Live kline updates (both closed and ticks) are published via Redis Pub/Sub.
    *   **Backend API for Klines:**
        *   `GET /data/klines/{symbol}/{timeframe}`: Fetches historical klines, intelligently utilizing Redis cache and TimescaleDB, and reports data backfill status.
        *   `GET /ws/klines/{symbol}/{timeframe}` (WebSocket): Streams live kline updates (closed klines and ticks) to frontend clients by subscribing to Redis Pub/Sub.
    *   **Frontend Live Mode:**
        *   Interactive "Live" / "Custom" chart mode switcher.
        *   Paginated fetching of historical klines when panning left in "Live" mode.
        *   Real-time chart updates from WebSocket data.
        *   UI indicators for data loading status and backfill progress (`ChartStatusPopup.vue`).

*   **Interactive Asset & Timeframe Selection:**
    *   `AssetTimeframeSelector.vue` component allows users to:
        *   Manually enter an asset symbol (e.g., "BTCUSDT").
        *   Select a timeframe from a dynamically populated list (e.g., "1m", "15m", "1H").
    *   Changes to asset or timeframe trigger:
        *   Clearing of current chart data.
        *   Context updates for News and Perflogs panels (asset change triggers data refresh).
        *   If in "Live" mode, re-fetches historical data and reconnects WebSocket for the new context.

*   **"Quick Look" News Panel:**
    *   **Backend:** A dedicated service (`backend/news_fetcher_service/`) polls the Marketaux API for news articles related to tracked symbols. Articles (including sentiment scores, images) are stored in PostgreSQL. An API endpoint (`/api/news/{symbol}`) serves this data.
    *   **Frontend:** A toggleable `NewsPanel.vue` displays news articles for the current chart symbol. Features include image previews, clickable headlines, source, publication date, sentiment display, and auto-refresh. Styled with a dark theme.

*   **"Perflogs" (Performance Logs) Feature:**
    *   Allows authenticated users to log and review their trading performance.
    *   **Backend:** `TradeNote` model in PostgreSQL (with asset, direction, entry/exit, P&L, etc.). CRUD operations and authenticated API endpoints (`/perflogs/notes/...`) are implemented.
    *   **Frontend:**
        *   Vuex module (`perflogs.js`) for state management.
        *   `PerflogsPanel.vue`: A toggleable right sidebar displaying trade notes for the current chart asset, summary P&L, and an "Add Note" form.
        *   `TradeNoteCard.vue`: Displays individual trade notes with details and a delete option.
        *   `AddTradeNoteForm.vue`: For creating new trade notes with client-side P&L calculation.
        *   Styled with a dark theme and uses Font Awesome icons.

*   **Development & Operational Environment:**
    *   Dockerized Redis for caching and Pub/Sub messaging.
    *   Dockerized TimescaleDB (PostgreSQL extension) for time-series kline data.
    *   Alembic for robust database schema migrations.

## 🛠️ Tech Stack

*   **Frontend:**
    *   Vue.js 2.x
    *   Vuex (v3) for state management
    *   Vue Router
    *   Axios for HTTP requests
    *   **Local `trading-vue-js` library** (from `frontend/src/trading-vue-core/`) for charting
    *   JavaScript (ES6+), HTML5, CSS3
    *   Font Awesome 5 (via CDN) for icons

*   **Backend:**
    *   Python 3.13
    *   FastAPI (with Pydantic for data validation)
    *   SQLAlchemy (ORM)
    *   Alembic (for database migrations)
    *   `passlib[bcrypt]` (for password hashing)
    *   `python-jose[cryptography]` (for JWT)
    *   `websockets` library (for Binance WebSocket client in ingestion service)
    *   `httpx` (for REST API calls in ingestion service)
    *   `pandas` (for CSV processing)
    *   Uvicorn (ASGI server)

*   **Database & Caching:**
    *   PostgreSQL (running in Docker with TimescaleDB extension)
    *   Redis (running in Docker)

*   **Containerization (Development):**
    *   Docker & Docker Compose (managing Redis & TimescaleDB services via `docker-compose.yml`)

*   **Testing:**
    *   Pytest (for backend unit and integration tests)
    *   `pytest-asyncio`

## 📂 Project Structure Highlights

```
inchart-seed-test2/
├── .env                    # Local environment variables (GITIGNORED)
├── .gitignore              # Root gitignore
├── backend/
│   ├── .venv/              # Python virtual environment (GITIGNORED)
│   ├── .gitignore          # Backend specific gitignore
│   ├── alembic/            # Alembic migration scripts
│   ├── app/                # Core FastAPI application logic
│   │   ├── main.py
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── crud.py         # Database CRUD operations
│   │   ├── routers/        # API route modules
│   │   ├── security.py
│   │   └── config.py
│   ├── data_ingestion_service/ # Standalone Binance data worker
│   │   ├── main.py
│   │   ├── binance_connector.py
│   │   └── historical_data_fetcher.py
│   ├── news_fetcher_service/   # Standalone news polling worker
│   │   └── main.py
│   ├── tests/                # Pytest tests for backend
│   └── requirements.txt
├── docker-compose.yml      # Docker Compose for dev services (DB, Redis)
├── frontend/
│   ├── .gitignore          # Frontend specific gitignore
│   ├── node_modules/       # (GITIGNORED)
│   ├── public/
│   │   └── index.html      # Main HTML (sets "InCharts" title)
│   ├── src/
│   │   ├── assets/
│   │   ├── components/     # Reusable Vue components (Uploaders, Panels, etc.)
│   │   ├── router/
│   │   ├── store/          # Vuex store (modules for auth, chart, news, perflogs)
│   │   ├── trading-vue-core/ # LOCAL trading-vue-js library source
│   │   └── views/          # Main page views (Home.vue, Login.vue, etc.)
│   ├── package.json
│   └── vue.config.js
├── CHANGELOG.md
├── DIARY.md
├── DOCUMENTATION.md
├── LICENSE.md
├── README.md               # This file
└── TASKS.md
```

## 🏁 Getting Started / Setup Instructions

Follow these instructions to set up and run the InChart project locally.

### Prerequisites

*   **Git:** For cloning the repository.
*   **Python 3.13 & Pip:** For the backend.
*   **Node.js & NPM:** For the frontend (Node v16-v18 recommended for Vue 2 compatibility).
*   **Docker Desktop:** For running Redis and TimescaleDB services. Ensure Docker is installed and running.

### 1. Clone the Repository

```bash
git clone <your-repository-url> # Replace with your actual repository URL
cd inchart-seed-test2 # Or your project's root folder name
```

### 2. Configure Environment Variables

*   In the project root directory (`inchart-seed-test2/`), create a file named `.env`.
*   Populate it with necessary configurations. Refer to `DOCUMENTATION.md` (Section 5) or `.env.example` (if provided) for required variables like:
    *   `DATABASE_URL=postgresql://inchart_admin:p3ace-0f-ouR-t!me@localhost:5433/inchart_db`
    *   `REDIS_HOST=localhost`
    *   `REDIS_PORT=6379`
    *   `SECRET_KEY` (for JWT)
    *   `ALGORITHM` (for JWT)
    *   `ACCESS_TOKEN_EXPIRE_MINUTES`
    *   `BINANCE_API_KEY` / `BINANCE_SECRET_KEY` (optional, for higher REST API rate limits)
    *   `PROACTIVE_SYMBOLS` / `PROACTIVE_TIMEFRAMES` (for data ingestion)
    *   `MARKETAUX_API_TOKEN` (for news service)
    *   ... and other settings as defined in `backend/app/config.py`.

### 3. Start Dependent Services (Docker Compose)

Ensure Docker Desktop is running. In the project root directory:

```bash
docker-compose up -d
```
This starts Redis and TimescaleDB. To check their status: `docker ps`.
To view logs: `docker-compose logs -f inchart_redis` or `docker-compose logs -f inchart_postgres_timescaledb`.

### 4. Backend Setup & Launch

*   **Navigate to Backend & Create Virtual Environment:**
    ```bash
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
*   **Install Dependencies:**
    ```bash
    # Ensure you are in the backend/ directory and venv is active
    pip install -r ../requirements.txt # If requirements.txt is in root
    # or pip install -r requirements.txt # If requirements.txt is in backend/
    ```
*   **Run Database Migrations:**
    (Ensure Docker services are running and `.env` is configured)
    ```bash
    # Ensure you are in the backend/ directory and venv is active
    alembic upgrade head
    ```
*   **Start FastAPI Server:**
    ```bash
    # Ensure you are in the backend/ directory and venv is active
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    API will be at `http://localhost:8000`, docs at `http://localhost:8000/docs`.

*   **Start Data Ingestion Service:**
    (In a *new terminal*, navigate to `backend/`, activate venv)
    ```bash
    python -m data_ingestion_service.main
    ```
    Monitor its console output for activity (backfilling, WebSocket connections).

*   **Start News Fetcher Service:**
    (In *another new terminal*, navigate to `backend/`, activate venv)
    ```bash
    python -m news_fetcher_service.main
    ```

### 5. Frontend Setup & Launch

*   **Navigate to Frontend & Install Dependencies:**
    ```bash
    cd frontend
    npm install
    ```
*   **(Optional) Linting:**
    ```bash
    npm run lint -- --fix
    ```
*   **Start Vue.js Development Server:**
    ```bash
    npm run serve
    ```
    The frontend is typically accessible at `http://localhost:8080`. The browser tab title will be "InCharts".

You should now be able to access the InChart application.

## 🗺️ Key Upcoming Features / Roadmap (Simplified)

Based on current plans (`TASKS.md`):

*   **Testing, Refinement & Documentation (Task 7.0 - Ongoing):**
    *   Backend unit & integration tests. `DONE`
    *   Frontend interaction testing (manual). `to_do`
    *   Performance & stability monitoring. `to_do`
    *   Update project documentation (README, DOCUMENTATION.md, etc.). `in_progress`
*   **Task 10.0: Final Testing & Documentation Update (Post-Perflogs)**: `to_do`
*   Future considerations: More advanced charting features, user watchlists, expanded backtesting capabilities.

## 🤝 Contributing

This project follows guidelines outlined in the `project_guidelines/` directory and `CRITICAL_RULES.md`. Please ensure adherence to these when contributing.

## 📜 License

This project is licensed under the terms of the MIT license. See `LICENSE.MD` for more details. 