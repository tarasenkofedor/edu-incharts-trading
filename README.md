# InChart 📊 - Trading Charting Platform MVP

InChart is a Minimum Viable Product (MVP) for a trading charting platform. It focuses on providing users with the ability to visualize cryptocurrency price data, upload their own custom OHLCV (Open, High, Low, Close, Volume) and signal data, and aims to integrate live price feeds from Binance.

A key characteristic of this project is its use of a local, "raw" version of the `trading-vue-js` library (Vue 2 compatible) for its charting capabilities, allowing for deep customization and control over the charting components.

## ✨ Overview

The primary goal of InChart is to offer a flexible charting tool that caters to users who want to analyze market data using standard charts, as well as those who wish to import and visualize their own datasets and trading signals. The platform is being built with a modern technology stack and aims for a clean, intuitive user interface.

## 🚀 Current Features

*   **User Authentication:**
    *   Secure user registration with nickname, email, and password.
    *   JWT-based login system.
*   **Charting Core (via local `trading-vue-js`):**
    *   Display of OHLCV candlestick charts.
    *   Interactive chart features: zooming, panning, and crosshair (performance optimized).
    *   Initial sample data display on load.
    *   Optimized rendering for signal overlays (`Trades.vue`) with horizontal culling and zoom-dependent label visibility for improved performance.
*   **Custom Data Upload:**
    *   **OHLCV Data:** Users can upload their own price data in CSV format (`timestamp,open,high,low,close,volume`).
    *   **Signal Data:** Users can upload custom trading signals (e.g., buy/sell markers) in CSV format (`timestamp,type,price,label,color,icon`), which are displayed as overlays on the chart.
*   **Backend:**
    *   Built with FastAPI (Python).
    *   PostgreSQL database (via TimescaleDB extension) for storing user and kline data.
    *   Alembic for database migrations.
*   **Frontend:**
    *   Developed using Vue.js 2.
    *   Vuex for state management.
    *   `axios` for API communication.
*   **Development Environment:**
    *   Dockerized Redis for caching and Pub/Sub messaging.
    *   Dockerized TimescaleDB (PostgreSQL extension) for time-series kline data.
*   **Live Price Data Integration (Binance):**
    *   **Data Ingestion Service:** Standalone background worker (`backend/data_ingestion_service/`) connects to Binance WebSockets for live kline data (e.g., BTCUSDT 1m).
    *   **Historical Backfill:** Service automatically backfills historical kline data from Binance REST API on startup and fills gaps.
    *   **Data Persistence & Caching:** Live and historical klines stored in TimescaleDB, most recent klines cached in Redis for fast API retrieval.
    *   **Real-time Updates:** New klines are published via Redis Pub/Sub.
    *   **Backend API:**
        *   `/data/klines/{symbol}/{timeframe}` (GET): Fetches historical klines, utilizing Redis cache and TimescaleDB, reports backfill status.
        *   `/ws/klines/{symbol}/{timeframe}` (WebSocket): Streams live kline updates to frontend clients by subscribing to Redis Pub/Sub.
    *   **Frontend Live Mode:**
        *   Switch between "Live" and "Custom" chart data modes.
        *   Fetches paginated historical klines for live charts.
        *   Receives real-time kline updates via WebSocket.
        *   Displays UI indicators for data loading and backfill status.

## 🛠️ Tech Stack

*   **Frontend:**
    *   Vue.js 2.x
    *   Vuex (v3)
    *   Axios
    *   Local `trading-vue-js` library (from `frontend/src/trading-vue-core/`)
*   **Backend:**
    *   Python 3.9+
    *   FastAPI
    *   SQLAlchemy (with Pydantic for data validation)
    *   Alembic (for database migrations)
    *   `passlib[bcrypt]` (for password hashing)
    *   `python-jose[cryptography]` (for JWT)
*   **Database:**
    *   PostgreSQL (running in Docker with TimescaleDB extension)
*   **Caching:**
    *   Redis (running in Docker)
*   **WebSockets:**
    *   FastAPI (for backend WebSocket endpoint)
    *   `websockets` library (Python, for Binance WebSocket client in ingestion service)
    *   Native Browser WebSockets (for frontend)
*   **Containerization (Development):**
    *   Docker
    *   Docker Compose (managing Redis & TimescaleDB services via `docker-compose.yml`)

## 📂 Project Structure

```
inchart-seed-test2/
├── .env.example            # Example environment variables
├── backend/                # FastAPI application
│   ├── .venv/              # Python virtual environment
│   ├── alembic/            # Alembic migration scripts
│   ├── app/                # Core application logic (main.py, models, schemas, routers, etc.)
│   └── requirements.txt    # Backend Python dependencies
├── docker-compose.yml      # Docker Compose configuration for dev services
├── frontend/               # Vue.js 2 application
│   ├── node_modules/       # Frontend dependencies
│   ├── public/
│   ├── src/                # Main frontend source code
│   │   ├── assets/
│   │   ├── components/
│   │   ├── router/
│   │   ├── store/
│   │   ├── trading-vue-core/ # Local trading-vue-js library source
│   │   └── views/
│   ├── babel.config.js
│   ├── package.json
│   └── vue.config.js
├── project_guidelines/     # Project rules and documentation standards
└── TASKS.md                # Detailed project tasks
```

## 🏁 Getting Started / Setup Instructions

Follow these instructions to set up and run the InChart project locally.

### Prerequisites

*   **Git:** For cloning the repository.
*   **Python 3.9+ & Pip:** For the backend.
*   **Node.js & NPM:** For the frontend (ensure Node.js version is compatible with Vue 2, e.g., Node v16-v18).
*   **Docker Desktop:** For running Redis and TimescaleDB services. (Ensure Docker Desktop is installed and the Docker engine is running).

### 1. Clone the Repository

```bash
git clone <your-repository-url> # Replace with your actual repository URL
cd inchart-seed-test2 # Or your project's root folder name
```

### 2. Backend Setup

*   **Create and Activate Python Virtual Environment:**
    ```bash
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate
    ```
    *(On Windows, use `backend\.venv\Scripts\activate`)*

*   **Install Dependencies:**
    ```bash
    pip install -r backend/requirements.txt
    ```

*   **Create `.env` File:**
    In the project root directory (`inchart-seed-test2/`), create a file named `.env`.
    Copy the contents from `.env.example` (which will be created in the next step) into this new `.env` file and fill in your actual database credentials and secrets.
    **Important:** Ensure your `DATABASE_URL` in the `.env` file points to the Dockerized TimescaleDB instance. Since we mapped host port 5433 to the container's 5432 port, the connection string should look like this:
    `postgresql://inchart_admin:p3ace-0f-ouR-t!me@localhost:5433/inchart_db`

*   **Run Database Migrations:**
    (Ensure your Dockerized TimescaleDB service is running - see step 4)
    ```bash
    cd backend
    ../.venv/bin/alembic upgrade head
    cd ..
    ```

### 3. Frontend Setup

*   **Navigate to Frontend Directory:**
    ```bash
    cd frontend
    ```
*   **Install Dependencies:**
    ```bash
    npm install
    ```
*   **(Optional) Linting:**
    If you encounter linting issues, you might want to run:
    ```bash
    npm run lint -- --fix
    ```
    Then, navigate back to the project root:
    ```bash
    cd ..
    ```

### 4. Running Dependent Services (Docker Compose)

Ensure Docker Desktop is running. In the project root directory, start the Redis and TimescaleDB services:

```bash
docker-compose up -d redis postgres-timescaledb
```
You can check their status with `docker ps`.

### 5. Running the Application

*   **Backend (FastAPI):**
    (Ensure your Python virtual environment is activated and you are in the project root)
    ```bash
    cd backend
    ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The backend API server should now be running on `http://localhost:8000`.

*   **Data Ingestion Service (Standalone Python Process):**
    (In a new terminal window/tab, ensure your Python virtual environment is activated and you are in the `backend/` directory)
    ```bash
    # From within the backend/ directory:
    python -m data_ingestion_service.main
    ```
    This service will connect to Binance, fetch data, and populate TimescaleDB/Redis. Monitor its console output for activity.

*   **Frontend (Vue.js):**
    (In a new terminal window/tab, navigate to the frontend directory)
    ```bash
    cd frontend
    npm run serve
    ```
    The frontend development server typically starts on `http://localhost:8080`.

You should now be able to access the InChart application in your browser at `http://localhost:8080`.

## 🗺️ Key Upcoming Features / Roadmap

Based on current plans (`TASKS.md`):

*   **Live Price Data Integration (Binance - Task 6.0):** `DONE`
    *   **Environment & Infrastructure:** Configure backend project for Dockerized Redis & TimescaleDB, define Kline data model and migrations. `DONE`
    *   **Backend Data Ingestion Service:** Develop a background worker to connect to Binance WebSockets, process live kline data, cache in Redis, and persist in TimescaleDB. Implement historical data backfill and gap-filling logic. `DONE`
    *   **Backend API:** Create API endpoints for frontend to fetch historical and (via WebSockets) live kline data. `DONE`
    *   **Frontend Integration:**
        *   Implement UI for switching between "Live" and "Custom" chart data modes. `DONE`
        *   Fetch and display paginated historical kline data for "Live" mode. `DONE`
        *   Establish frontend WebSocket connection to backend for real-time kline updates in "Live" mode. `DONE`
        *   Handle data synchronization and UI feedback during mode switches and data loading. `DONE`
*   **Testing, Refinement & Documentation (Task 7.0):**
    *   Backend unit & integration tests. `DONE`
    *   Frontend interaction testing. `to_do`
    *   Performance & stability monitoring. `to_do`
    *   Update project documentation. `in_progress`
*   **Advanced Charting Features & Data Management (Task 5.0 - Placeholder):**
    *   Further enhancements to charting capabilities and data management (specifics to be defined).

## 🤝 Contributing

This project follows guidelines outlined in the `project_guidelines/` directory. Please ensure adherence to these when contributing. (Further details can be added as the project evolves).

## 📜 License

This project is licensed under the terms of the MIT license. See `LICENSE.MD` for more details. 