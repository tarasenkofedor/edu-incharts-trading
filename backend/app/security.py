"""
@file: security.py
@description: Security-related utilities (password hashing, JWT handling, auth dependencies).
@dependencies: fastapi, passlib, python-jose, datetime, sqlalchemy.orm, backend.app.config, backend.app.schemas, backend.app.crud, backend.app.database, backend.app.models
@created: [v4] 2025-05-18
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError # Keep for Pydantic-related errors if any
from sqlalchemy.orm import Session

from .config import settings
from .schemas import TokenData # User schema for return type - No, User is for response model, models.User is for internal
from . import crud, models # For fetching user from DB and models.User type hint
from .database import get_db # For DB session dependency

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
# OAuth2PasswordBearer scheme
# tokenUrl should point to your login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# JWT Token Creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Ensure ACCESS_TOKEN_EXPIRE_MINUTES is an int, provide default if None
        expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if settings.ACCESS_TOKEN_EXPIRE_MINUTES is not None else 15
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not configured")
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user: Optional[models.User] = None # Explicitly Optional before assignment
    try:
        if not settings.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY not configured for token verification") 
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        nickname: Optional[str] = payload.get("sub")
        if nickname is None:
            raise credentials_exception
        # token_data = TokenData(nickname=nickname) # No need to create TokenData if only using nickname string
    except JWTError:
        raise credentials_exception
    except ValueError as e: 
        print(f"Internal configuration error: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal configuration error regarding JWT."
        )
    # Pydantic ValidationError for TokenData is removed as we are not creating it here if not needed
    
    if nickname: # Ensure nickname was extracted
        user = crud.get_user_by_nickname(db, nickname=nickname)
    
    if user is None:
        raise credentials_exception
    return user # Type is now confirmed to be models.User due to the check above

async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# JWT Token Decoding/Verification (will be expanded in Task 1.5)
# For now, a placeholder or basic structure if needed by registration success
# def verify_access_token(token: str, credentials_exception) -> Optional[TokenData]:
#     try:
#         if not settings.JWT_SECRET_KEY:
#             raise ValueError("JWT_SECRET_KEY not configured")
#         payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
#         nickname: Optional[str] = payload.get("sub") # Or whatever key you use for user identifier
#         if nickname is None:
#             # For Pydantic V2, handle validation error appropriately
#             # For V1, this might raise a different error or None
#             raise credentials_exception 
#         token_data = TokenData(nickname=nickname)
#     except (JWTError, ValidationError):
#         raise credentials_exception
#     return token_data 