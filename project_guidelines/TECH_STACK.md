# Project InChart - Technology Stack

## Overview
This document outlines the technology stack for the InChart trading platform. The choices are guided by the project requirements, including the use of the `trading-vue-js` charting library, the need for real-time data handling, Python script execution, user authentication, subscription management, and scalability for at least 1000 concurrent users, all within a 5-day MVP timeline.

## Frontend
*   **Framework:** Vue.js
    *   **Version: Strictly 2.x.** This is a critical requirement as `trading-vue-js` is built for Vue 2 and is incompatible with Vue 3. All Vue.js project initialization and development must use Vue 2.x.
    *   **Rationale:** Required by the chosen `trading-vue-js` charting library. Vue.js 2 is a progressive framework, good for SPAs, and has a strong ecosystem.
    *   **Consideration:** `trading-vue-js` is not actively maintained. We may need to fork and patch it or allocate time for bug fixing.
*   **Charting Library:** `trading-vue-js`
    *   **Rationale:** Chosen by the client. Offers hackability for custom indicators and signals.
*   **State Management:** Vuex (Standard for Vue 2)
    *   **Rationale:** Manages complex application state effectively.
*   **HTTP Client:** Axios
    *   **Rationale:** Promise-based HTTP client for browser and Node.js, widely used and reliable.
*   **Styling:**
    *   CSS Framework: Tailwind CSS or a lightweight utility-first framework.
    *   Custom CSS for minimalistic, Apple-like design.
    *   **Rationale:** Tailwind provides utility classes for rapid UI development while allowing for custom design aesthetics.

## Backend
*   **Language/Framework:** Python 3.9+ with FastAPI
    *   **Rationale:**
        *   Excellent for building APIs quickly (MVP focus).
        *   Native async support, crucial for handling websockets and concurrent connections.
        *   Directly facilitates the execution of user-provided Python scripts for signal generation.
        *   Strong ecosystem for data processing and financial libraries.
*   **Database:** PostgreSQL (Latest stable version)
    *   **Rationale:**
        *   Robust, reliable, and feature-rich relational database.
        *   Handles structured data (users, subscriptions, historical prices) effectively.
        *   Good support for JSONB if needed for flexible signal data or metadata.
        *   Scales well and supports concurrent connections.
        *   **Development Environment:** Currently running via Docker using the `timescale/timescaledb:latest-pg16` image, managed by `docker-compose.yml`.
*   **Database Migration Tool:** Alembic
    *   **Rationale:**
        *   Integrates with SQLAlchemy to manage database schema changes incrementally.
        *   Provides a robust way to version database schemas and apply changes reliably.
        *   Essential for evolving the database schema without manual SQL or data loss.
*   **Caching:** Redis (Latest stable version)
    *   **Rationale:**
        *   High-performance in-memory data store.
        *   Essential for caching live price data from Binance to reduce latency and API calls.
        *   Can be used for session management or rate limiting.
        *   **Development Environment:** Currently running via Docker using the `redis:alpine` image, managed by `docker-compose.yml`.
*   **Websockets:** FastAPI's native WebSocket support.
    *   **Rationale:** Integrated into the framework, simplifies real-time communication for live data and signals.
*   **Authentication & Authorization:** JWT (JSON Web Tokens)
    *   **Rationale:**
        *   Stateless, suitable for SPAs and microservices.
        *   Simpler to implement for MVP compared to full OAuth.
        *   Secure if implemented correctly (HTTPS, short-lived tokens, refresh tokens).
*   **Python Script Execution:**
    *   **MVP:** Direct execution within a secured FastAPI endpoint (e.g., using `subprocess` with strict input validation and resource limits).
    *   **Long-term:** Dedicated sandboxed environment (e.g., Docker containers per script, or a service like `AWS Lambda` or `Google Cloud Functions`) for security and isolation.
*   **Task Queues (Post-MVP):** Celery with Redis/RabbitMQ
    *   **Rationale:** For handling background tasks like complex signal calculations, report generation, or email notifications without blocking API responses.

## Data Ingestion & Processing
*   **Binance Data:** Python `websockets` library or `python-binance` library for connecting to Binance WebSocket streams.
    *   **Rationale:** Efficient real-time data fetching.
*   **News Data:** Marketaux API (`marketaux.com`)
    *   **Rationale:** Provides financial news articles with sentiment analysis, used for the "Quick Look" news feature.
*   **Data Validation:** Pydantic (comes with FastAPI)
    *   **Rationale:** Ensures data integrity for price data (format, sorting by timestamp) and user inputs.

## Payments
*   **Payment Gateway:** Stripe
    *   **Rationale:** Developer-friendly APIs, widely adopted, handles subscriptions and PCI compliance. Python SDK available.

## DevOps & Hosting
*   **Hosting:** Contabo VPS (Linux - Ubuntu LTS recommended)
*   **Web Server:** Uvicorn (ASGI server for FastAPI)
*   **Process Manager:** Gunicorn (for managing Uvicorn workers) or `systemd`.
*   **Reverse Proxy:** Nginx or Caddy
    *   **Rationale:** Handles SSL termination, load balancing (if scaling horizontally later), serving static files, and security headers. Caddy offers automatic HTTPS.
*   **Containerization (Recommended Post-MVP):** Docker, Docker Compose
    *   **Rationale:** Simplifies deployment, environment consistency, and scaling.
    *   **Current Usage:** Docker and Docker Compose are actively used in the development environment for managing PostgreSQL/TimescaleDB and Redis services.

## Key Considerations
*   **Security:**
    *   HTTPS everywhere.
    *   Input validation (Pydantic for backend, frontend validation).
    *   Protection against common web vulnerabilities (OWASP Top 10).
    *   Secure execution of Python scripts (sandboxing is critical long-term).
*   **Scalability:**
    *   FastAPI and PostgreSQL are capable of handling 1000+ concurrent users with proper configuration and sufficient server resources.
    *   Redis caching is key for performance.
    *   Stateless backend services (JWT) allow easier horizontal scaling.
*   **Data Integrity:**
    *   Backend must enforce timestamp sorting for all price/signal data.
    *   Transactional integrity for user and subscription data in PostgreSQL. 