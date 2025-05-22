"""
@file: crud.py
@description: Create, Read, Update, Delete (CRUD) operations for database models.
@dependencies: sqlalchemy.orm, backend.app.models, backend.app.schemas, backend.app.security
@created: [v3] 2025-05-18
"""
from sqlalchemy.orm import Session
from typing import Optional

from . import models, schemas
from .security import get_password_hash

# User CRUD operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_nickname(db: Session, nickname: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.nickname == nickname).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        nickname=user.nickname,
        hashed_password=hashed_password
        # first_joined_at is server_default
        # is_active is default=True
        # subscription_plan is default=FREE
        # start_of_subscription and end_of_subscription are nullable
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# def update_user(...): # To be implemented later if needed for Task 3.5.x
#     pass

# def delete_user(...): # To be implemented later if needed
#     pass

# --- TradeNote CRUD Operations ---

def create_trade_note(db: Session, trade_note: schemas.TradeNoteCreate, user_id: int) -> models.TradeNote:
    """Create a new trade note for a user."""
    # Exclude trade_direction from the initial dump, as we'll handle it directly
    db_trade_note_data = trade_note.model_dump(exclude={'trade_direction'})
    
    print(f"[CRUD - trade_note.trade_direction Pydantic model attr]: {trade_note.trade_direction}") # Debug
    print(f"[CRUD - type(trade_note.trade_direction) Pydantic model attr]: {type(trade_note.trade_direction)}") # Debug
    
    # Initialize the SQLAlchemy model, passing the enum member's .value explicitly
    db_trade_note = models.TradeNote(
        **db_trade_note_data,
        trade_direction=trade_note.trade_direction.value,  # Explicitly pass the enum member's value
        user_id=user_id
    )
    
    print(f"[CRUD - db_trade_note.trade_direction before add/commit]: {db_trade_note.trade_direction}") # Debug
    print(f"[CRUD - type(db_trade_note.trade_direction) before add/commit]: {type(db_trade_note.trade_direction)}") # Debug
    
    db.add(db_trade_note)
    db.commit()
    db.refresh(db_trade_note)
    return db_trade_note

def get_trade_notes_by_user_and_asset(db: Session, user_id: int, asset_ticker: str, skip: int = 0, limit: int = 100) -> list[models.TradeNote]:
    """Get all trade notes for a specific user and asset, ordered by creation date (newest first)."""
    return (
        db.query(models.TradeNote)
        .filter(models.TradeNote.user_id == user_id, models.TradeNote.asset_ticker == asset_ticker)
        .order_by(models.TradeNote.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_trade_note_by_id(db: Session, trade_note_id: int, user_id: int) -> Optional[models.TradeNote]:
    """Get a specific trade note by its ID, ensuring it belongs to the user."""
    return (
        db.query(models.TradeNote)
        .filter(models.TradeNote.id == trade_note_id, models.TradeNote.user_id == user_id)
        .first()
    )

def delete_trade_note(db: Session, trade_note_id: int, user_id: int) -> Optional[models.TradeNote]:
    """Delete a specific trade note by its ID, ensuring it belongs to the user.
    Returns the deleted note object if found and deleted, otherwise None.
    """
    db_trade_note = (
        db.query(models.TradeNote)
        .filter(models.TradeNote.id == trade_note_id, models.TradeNote.user_id == user_id)
        .first()
    )
    if db_trade_note:
        db.delete(db_trade_note)
        db.commit()
        return db_trade_note
    return None 