"""
@file: main.py
@description: Main FastAPI application entry point.
@dependencies: fastapi, .routers.auth, .routers.users, .routers.data, fastapi.middleware.cors, starlette.middleware.trustedhost
@created: [v1] 2025-05-18
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
# from starlette.middleware.trustedhost import TrustedHostMiddleware # Temporarily commented out
from .routers import auth, users, data, news, perflogs # Add perflogs router
from .routers import config as config_router # Added for config endpoints
from .database import engine, Base 
from . import models
from .config import settings

# Create all tables in the database.
# For production, you might want to handle migrations with Alembic separately.
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InChart API",
    description="API for the InChart trading platform services.",
    version="0.1.0" # Corresponds to VERSION file, will be updated for releases
)

# TrustedHost Middleware Configuration - Add this BEFORE CORS
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["*"]  # Allow ALL hosts for testing
# )

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(data.router, prefix="/data", tags=["Data Services"]) # Updated tag
app.include_router(news.router, prefix="/api", tags=["News"]) # Corrected: Added /api prefix back for consistency
app.include_router(perflogs.router, prefix="/api") # Added perflogs router with /api prefix
app.include_router(config_router.router) # Register the new config router

@app.get("/ping", summary="Health check", tags=["Health"])
async def ping():
    """Simple health check endpoint."""
    return {"message": "pong! from InChart API v" + "0.1.0"} 

@app.get("/info")
async def info():
    return {
        "app_name": app.title,
        "version": app.version,
        "description": app.description,
        "settings": {
            "database_url_type": type(settings.DATABASE_URL).__name__,
            "redis_host": settings.REDIS_HOST,
            "redis_port": settings.REDIS_PORT,
            "secret_key_set": "********" if settings.SECRET_KEY else "Not Set",
            "algorithm": settings.ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        }
    } 