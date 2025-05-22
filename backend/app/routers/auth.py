"""
@file: auth.py
@description: API router for authentication (registration, login).
@dependencies: fastapi, sqlalchemy.orm, backend.app.schemas, backend.app.crud, backend.app.security, backend.app.database
@created: [v3] 2025-05-18
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # For login later
from sqlalchemy.orm import Session

from .. import crud, models, schemas, security
from ..database import get_db

router = APIRouter(
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    - **email**: Each email must be unique.
    - **nickname**: Each nickname must be unique.
    - **password**: Min length 8.
    """
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    db_user_by_nickname = crud.get_user_by_nickname(db, nickname=user.nickname)
    if db_user_by_nickname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nickname already taken"
        )
    created_user = crud.create_user(db=db, user=user)
    # Optionally, create and return a token immediately upon registration (Task 1.5 might refine this)
    # access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    # access_token = security.create_access_token(
    #     data={"sub": created_user.nickname}, expires_delta=access_token_expires
    # )
    # return {"access_token": access_token, "token_type": "bearer", "user": created_user} # Example with token
    return created_user # Returning the user object as per response_model=schemas.User

# Login endpoint will be added in Task 1.4
@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT token.
    Accepts form data with `username` (can be email or nickname) and `password`.
    """
    user = crud.get_user_by_nickname(db, nickname=form_data.username)
    if not user:
        user = crud.get_user_by_email(db, email=form_data.username)
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect nickname/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    access_token = security.create_access_token(
        data={"sub": user.nickname} # Using nickname as subject in token
    )
    return {"access_token": access_token, "token_type": "bearer"} 