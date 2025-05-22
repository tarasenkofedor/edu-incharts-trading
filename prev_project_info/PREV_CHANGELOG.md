# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- N/A
### Changed
- N/A
### Fixed
- N/A

## [0.0.14] - 2025-05-19
### Added
- Alembic for database migrations (`alembic`).
- Initial Alembic migration to create `users` table with `id`, `email`, `nickname`, `hashed_password`, `is_active` columns and appropriate indexes.

### Changed
- Backend database schema is now managed by Alembic.
- `backend/requirements.txt` updated with `alembic`.
- `backend/alembic.ini` and `backend/alembic/env.py` configured for the project.
- `docs/project_guidelines/TECH_STACK.md` updated to include Alembic.
- `.cursor/rules/python_packaging.mdc` rule created.
- `docs/project_guidelines/CRITICAL_RULES.md` updated for `.env` file usage.

### Fixed
- Resolved `sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column users.nickname does not exist` by ensuring the `users` table is created via Alembic with the `nickname` column.

## [0.0.13] - 2025-05-18
### Fixed
- **Chart Data Display Issue:** Resolved an issue where uploaded OHLCV price data was successfully processed by the backend and a success message was shown, but the data did not render on the `TradingChart.vue` component.
  - **Root Cause:** The `trading-vue-js` library (and the wrapper `TradingChart.vue`) expects its main data prop (`data` for the library, `chartData` for the wrapper) to be an `Object` (e.g., `{ chart: { type: 'Candles', data: [...] } }`), but `App.vue` was initially passing an `Array`.
  - **Solution:**
    - Modified `frontend/src/App.vue`:
      - Initialized `ohlcvData` in the `data()` section to be an object conforming to the `trading-vue-js` expected structure (e.g., `{ chart: { type: 'Candles', data: [] } }`).
      - Updated the `handlePriceDataUploaded` method to correctly populate the `chart.data` array *within* the `ohlcvData` object.
    - Verified `frontend/src/components/TradingChart.vue` was already correctly expecting an `Object` for its `chartData` prop.
  - This resolved the Vue prop type warnings on initial load and after data upload, and the chart now correctly displays the uploaded data.
- **Anonymous Session Token Validation (`/users/me`):** Fixed a `500 Internal Server Error` on `GET /users/me` when an anonymous session token was active. 
  - **Root Cause:** The placeholder email `anonymous@session.local` used for anonymous users in `backend/app/security.py` was failing Pydantic's `EmailStr` validation because `.local` is a reserved TLD.
  - **Solution:** Changed the placeholder email to `anonymous@example.com` in `backend/app/security.py`, which passes `EmailStr` validation.

## [v8] - 2025-05-18
### Fixed
- **Chart Data Display Issue:** Resolved an issue where uploaded OHLCV price data was successfully processed by the backend and a success message was shown, but the data did not render on the `TradingChart.vue` component.
  - **Root Cause:** The `trading-vue-js` library (and the wrapper `TradingChart.vue`) expects its main data prop (`data` for the library, `chartData` for the wrapper) to be an `Object` (e.g., `{ chart: { type: 'Candles', data: [...] } }`), but `App.vue` was initially passing an `Array`.
  - **Solution:**
    - Modified `frontend/src/App.vue`:
      - Initialized `ohlcvData` in the `data()` section to be an object conforming to the `trading-vue-js` expected structure (e.g., `{ chart: { type: 'Candles', data: [] } }`).
      - Updated the `handlePriceDataUploaded` method to correctly populate the `chart.data` array *within* the `ohlcvData` object.
    - Verified `frontend/src/components/TradingChart.vue` was already correctly expecting an `Object` for its `chartData` prop.
  - This resolved the Vue prop type warnings on initial load and after data upload, and the chart now correctly displays the uploaded data.
- **Anonymous Session Token Validation (`/users/me`):** Fixed a `500 Internal Server Error` on `GET /users/me` when an anonymous session token was active. 
  - **Root Cause:** The placeholder email `anonymous@session.local` used for anonymous users in `backend/app/security.py` was failing Pydantic's `EmailStr` validation because `.local` is a reserved TLD.
  - **Solution:** Changed the placeholder email to `anonymous@example.com` in `backend/app/security.py`, which passes `EmailStr` validation.

## [v7] - 2025-05-18
### Added
- **Task 3.3: Chart Population with Custom Price Data**
  - Implemented frontend logic to connect `PriceDataUploader.vue` to the backend API.
  - `PriceDataUploader.vue` now uses `axios` to POST to `/api/data/upload/price` (proxied to backend) and emits `price-data-uploaded` event with validated OHLCV data.
  - `vue.config.js` updated to include dev server proxy for `/api` to `http://localhost:8000`.
  - `App.vue` now handles the `price-data-uploaded` event, transforms the data to the format required by `trading-vue-js`, and updates the `TradingChart.vue` component via its `chartData` prop.
  - `TradingChart.vue` updated to correctly use the `chartData` prop and default to an empty state.
  - Backend endpoint `/data/upload/price` in `data.py` modified to return the full validated OHLCV data under the `data` key.

## [v6] - 2025-05-18
### Added
- **Task 3.2: Backend API Endpoint for Price Data Upload**
  - Created `backend/app/routers/data.py` with a JWT-protected endpoint `/data/upload/price`.
  - Endpoint uses `pandas` to validate uploaded CSV files for OHLCV data (headers: `timestamp,open,high,low,close,volume`, data types, timestamp uniqueness and ascending order).
  - Added `python-multipart` and `pandas` to `backend/requirements.txt`.
  - Registered the new data router in `backend/app/main.py`.

## [v5] - 2025-05-18
### Added
- **Task 3.1: Frontend Price Data Upload UI (Static)**
  - Created `frontend/src/components/PriceDataUploader.vue` with a file input for CSVs, an upload button, and basic styling.
  - Integrated `PriceDataUploader.vue` into `frontend/src/App.vue`.

## [v4] - 2025-05-18
### Added
- **Task 2.3: Asset/Timeframe UI Component (Static)**
  - Created `frontend/src/components/AssetTimeframeSelector.vue` with static placeholders for asset and timeframe.
  - Applied basic Apple-like styling and positioned it over the chart area in `App.vue`.
  - Made `TradingChart.vue` in `App.vue` responsive to window size.

## [v3] - 2025-05-18
### Added
- **Task 2.2: Basic Charting Component Integration**
  - Created `frontend/src/components/TradingChart.vue` to encapsulate the `trading-vue-js` library.
  - Populated `TradingChart.vue` with minimal static/placeholder OHLCV data to verify rendering.
  - Integrated `TradingChart.vue` into the main `frontend/src/App.vue`, replacing default content.

## [v2] - 2025-05-18
### Added
- Initial project planning and documentation setup
- Created `DIARY.md` for logging all AI actions and results
- Added rules for mandatory action logging and context checks in `DIARY.md`
- Added rules for error logging in `ERROR_LOG.md`
- Updated `README.md` with project description, features, tech stack, and attribution
- Added and enforced canonical rule files in `docs/project_guidelines/`
- Initial FastAPI backend project structure (`backend/` directory, `app/main.py`, `app/__init__.py`, `requirements.txt`, `.gitignore`).
- Basic PostgreSQL database setup for FastAPI backend:
    - Pydantic models for User/Token (`schemas.py`).
    - SQLAlchemy User model (`models.py`).
    - Database session management (`database.py`).
    - Initial table creation in `main.py`.
- User registration endpoint (`/auth/register`):
    - Password hashing using `passlib[bcrypt]` (`security.py`).
    - FastAPI router for authentication (`routers/auth.py`).
    - Basic API tests for registration (success and duplicate email) using `pytest` and in-memory SQLite (`test/auto_tests/test_auth.py`).
- User login endpoint (`/auth/login`):
    - JWT token generation (`create_access_token` in `security.py`) using `python-jose`.
    - Endpoint uses `OAuth2PasswordRequestForm` and returns an access token.
    - API tests for login (success, incorrect password, non-existent user, inactive user) in `test/auto_tests/test_auth.py`.
- JWT Authentication Middleware/Dependencies:
    - Implemented JWT decoding (`jwt.decode`) and dependency `get_current_active_user` (using `OAuth2PasswordBearer`) in `security.py`.
    - Created `users` router (`routers/users.py`) with a protected `/users/me` endpoint.
    - API tests for `/users/me` endpoint (success, no token, invalid token, inactive user) in `test/auto_tests/test_users.py`.

### Changed
- Updated rule files to require logging and context checks

### Fixed
- N/A 