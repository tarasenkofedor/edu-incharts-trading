"""
Global fixtures for backend tests.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import AsyncGenerator, Generator

from backend.app.main import app  # Main FastAPI application
from backend.app.database import Base, get_db
from backend.app.config import settings

# Use a separate in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///./test.db"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST, connect_args={"check_same_thread": False}
)
SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

@pytest_asyncio.fixture(scope="function")
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Asynchronous test client for FastAPI app.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Provides a clean database session for each test function.
    Creates all tables and drops them after the test.
    """
    Base.metadata.create_all(bind=engine_test)  # Create tables
    db = SessionLocalTest()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test) # Drop tables

@pytest.fixture(scope="function")
def override_get_db(db_session: Session):
    """
    Fixture to override the get_db dependency with the test database session.
    """
    try:
        app.dependency_overrides[get_db] = lambda: db_session
        yield
    finally:
        del app.dependency_overrides[get_db]

# Potentially, a fixture for a real Redis client if needed for integration tests,
# configured to connect to a test Redis instance or mock Redis.
# For now, Redis interactions will likely be mocked at a lower level in unit tests.

# Similarly, for TimescaleDB, if direct interaction is needed for some tests beyond
# what the SQLite mock can cover, a fixture managing connection to the
# Dockerized TimescaleDB (perhaps with a dedicated test DB name) would go here. 