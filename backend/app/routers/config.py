"""
@file: config.py (router)
@description: API endpoints for application configuration settings.
@created: 2025-05-23
"""

from fastapi import APIRouter, Depends
from typing import List

from app.config import settings # Import the global settings instance

router = APIRouter(
    prefix="/api/config",
    tags=["Application Configuration"],
    responses={404: {"description": "Not found"}},
)

@router.get("/proactive-timeframes", response_model=List[str])
async def get_proactive_timeframes():
    """
    Retrieves the list of proactively tracked timeframes configured for the application.
    These are typically used by the data ingestion service and can be used by the
    frontend to populate timeframe selection UI.
    """
    return settings.PROACTIVE_TIMEFRAMES_LIST 