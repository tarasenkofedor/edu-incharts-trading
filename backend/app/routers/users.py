"""
@file: users.py
@description: API router for user-related operations (e.g., get current user).
@dependencies: fastapi, backend.app.schemas, backend.app.security, backend.app.models
@created: [v4] 2025-05-18
"""
from fastapi import APIRouter, Depends

from .. import models, schemas, security

router = APIRouter(
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(security.get_current_active_user)):
    """
    Fetch the current logged-in user.
    Requires authentication.
    """
    return current_user 