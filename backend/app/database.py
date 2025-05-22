"""
@file: database.py
@description: Database connection and session management setup.
@dependencies: sqlalchemy, backend.app.config
@created: [v2] 2025-05-18
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Ensure Base is imported if you plan to run create_all from here, though Alembic handles it.
# from backend.app.models import Base 
from .models import Base
from .config import settings

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session in path operations
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables (useful for initial setup without Alembic or for tests)
# However, for production and development with migrations, Alembic is preferred.
# def init_db():
#     Base.metadata.create_all(bind=engine) 