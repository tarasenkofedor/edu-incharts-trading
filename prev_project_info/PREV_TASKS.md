# InChart Project Tasks

This document outlines all development tasks for the InChart MVP. Tasks are managed according to [`TASK_RULES.md`](mdc:docs/project_guidelines/TASK_RULES.md).

---

## 1.0 Foundational Setup & User Accounts
   - **Status:** `done`
   - **Description:** Setup backend (FastAPI), database (PostgreSQL), and implement basic user registration and login with JWT authentication.
   - **Dependencies:** None

   ### 1.1 Backend Project Initialization (FastAPI)
      - **Status:** `done`
      - **Description:** Create FastAPI project structure, basic configuration, and dependencies (`uvicorn`, `psycopg2-binary`, `passlib[bcrypt]`, `python-jose[cryptography]`).
   ### 1.2 Database Setup (PostgreSQL)
      - **Status:** `done`
      - **Description:** Define User model (email, hashed_password, selected_plan). Setup database connection in FastAPI. Create initial database schema/tables.
   ### 1.3 User Registration Endpoint
      - **Status:** `done`
      - **Description:** Implement `/auth/register` endpoint. Accepts email & password, stores hashed password, returns JWT.
   ### 1.4 User Login Endpoint
      - **Status:** `done`
      - **Description:** Implement `/auth/login` endpoint. Accepts email & password, verifies credentials, returns JWT.
   ### 1.5 JWT Authentication Middleware/Dependencies
      - **Status:** `done`
      - **Description:** Implement JWT token generation, validation, and secure endpoint dependencies in FastAPI.

## 2.0 Core Charting Shell (Vue.js & `trading-vue-js`)
   - **Status:** `done`
   - **Description:** Integrate `trading-vue-js` into a new Vue.js application. Create the basic UI shell including the unified asset/timeframe selection component.
   - **Dependencies:** 1.0

   ### 2.1 Vue.js Project Setup
      - **Status:** `done`
      - **Description:** Initialize Vue.js (v2) project. Install `trading-vue-js`, `axios`, and `vuex`.
   ### 2.2 Basic Charting Component Integration
      - **Status:** `done`
      - **Description:** Create a main view/component that embeds the `trading-vue-js` chart component. Populate with minimal static/placeholder data initially to verify rendering.
   ### 2.3 Asset/Timeframe UI Component (Static)
      - **Status:** `done`
      - **Description:** Design and implement the UI for the asset/timeframe selector in the top-left of the chart area. Initially, it will be static (displaying placeholders, non-functional clicks).
      - **Styling:** Minimalistic, Apple-like design.
   ### 2.4 Fix Chart Zoom Functionality
      - **Status:** `pending`
      - **Description:** Investigate and resolve an issue where the chart zooms out on mouse scroll up, but does not zoom in on mouse scroll down. Ensure both zoom in and zoom out work correctly via mouse wheel.
      - **Dependencies:** 2.2

## 3.0 Custom Price Data (OHLCV) Upload & Display
   - **Status:** `done`
   - **Description:** Implement frontend UI for CSV upload, backend processing (validation, storage/forwarding), and display of custom OHLCV data on the chart. **Allows unauthenticated users to upload and view their own price data.**
   - **Dependencies:** 2.2

   ### 3.1 Frontend Price Data Upload UI
      - **Status:** `done`
      - **Description:** Create Vue component for CSV file input for OHLCV data.
   ### 3.2 Backend API Endpoint for Price Data Upload
      - **Status:** `done`
      - **Description:** Create FastAPI endpoint to receive OHLCV CSV. Validate format (`timestamp,open,high,low,close,volume`), ensure timestamps are sorted ascending. For MVP, can store in a temporary structure or pass through; DB storage can be a later refinement if time is critical.
   ### 3.3 Chart Population with Custom Price Data
      - **Status:** `done`
      - **Description:** Frontend logic to send uploaded CSV to backend, receive processed data, and update the `trading-vue-js` chart data object.

## 3.5 User Authentication UI & Nickname Integration
   - **Status:** `pending`
   - **Description:** Implement UI components for user login and registration, integrate them with the Vuex store, and add nickname functionality.
   - **Dependencies:** 1.0, Vuex Store Setup (implicitly done alongside Task 3.0 fixes)

   ### 3.5.1 Login Component Enhancements for Nickname
      - **Status:** `done`
      - **Description:** Update Vue component for user login to use `nickname` instead of email. On submit, dispatch Vuex 'login' action with nickname. Handle success/error responses.
   ### 3.5.2 Registration Component Enhancements for Nickname
      - **Status:** `done`
      - **Description:** Update registration component UI to include a `nickname` field. Update Vuex action for registration.
   ### 3.5.2.1 Create Vuex action for registration
      - **Status:** `done`
      - **Description:** Move the registration API call from the component to a dedicated Vuex action for better state management and consistency. (Note: Will be updated for nickname in 3.5.8)
   ### 3.5.2.2 Implement auto-login after successful registration
      - **Status:** `done`
      - **Description:** After a user successfully registers, automatically dispatch the login action and redirect them to the main application page. (Note: Will be updated for nickname in 3.5.8)
   ### 3.5.2.3 Enhance error handling and user feedback in Register component
      - **Status:** `done`
      - **Description:** Improve error messages and user feedback during the registration process, leveraging the Vuex action. (Note: Will be updated for nickname)
   ### 3.5.3 Display User Nickname / Logout Button
      - **Status:** `done` 
      - **Description:** Implement UI elements to display user login status (e.g., show username if logged in) and a logout button that dispatches the Vuex 'logout' action. (Base functionality exists, will be enhanced by 3.5.7)
   ### 3.5.4 Backend: Update User Model & Schemas for Nickname
      - **Status:** `done`
      - **Description:** Add a unique `nickname` field to the User SQLAlchemy model and update Pydantic schemas (`UserCreate`, `User` response, `TokenData` if needed).
      - **Dependencies:** 1.2
   ### 3.5.5 Backend: Update Registration Logic for Nickname
      - **Status:** `done`
      - **Description:** Modify `/auth/register` endpoint to accept `nickname`, validate its uniqueness, and store it.
      - **Dependencies:** 1.3, 3.5.4
   ### 3.5.6 Backend: Update Login Logic for Nickname
      - **Status:** `done`
      - **Description:** Modify `/auth/login` endpoint to authenticate users via `