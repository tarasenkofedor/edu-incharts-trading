from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, crud, models
from ..database import SessionLocal
from ..security import get_current_active_user

router = APIRouter(
    prefix="/perflogs",
    tags=["Perflogs"],
    responses={404: {"description": "Not found"}},
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/notes/", response_model=schemas.TradeNoteRead, status_code=status.HTTP_201_CREATED)
async def create_trade_note_for_user(
    trade_note: schemas.TradeNoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Create a new trade note for the authenticated user.
    """
    return crud.create_trade_note(db=db, trade_note=trade_note, user_id=current_user.id)

@router.get("/notes/{asset_ticker}", response_model=List[schemas.TradeNoteRead])
async def read_trade_notes_for_user_asset(
    asset_ticker: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Retrieve trade notes for the authenticated user and a specific asset ticker.
    """
    # TODO: Consider if asset_ticker should be path-encoded if it can contain special characters.
    # For now, assuming simple tickers.
    trade_notes = crud.get_trade_notes_by_user_and_asset(
        db=db, user_id=current_user.id, asset_ticker=asset_ticker, skip=skip, limit=limit
    )
    return trade_notes

@router.delete("/notes/{trade_note_id}", response_model=schemas.TradeNoteRead)
async def delete_trade_note_for_user(
    trade_note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Delete a specific trade note for the authenticated user.
    The user must be the owner of the note.
    """
    db_trade_note = crud.delete_trade_note(db=db, trade_note_id=trade_note_id, user_id=current_user.id)
    if db_trade_note is None:
        raise HTTPException(status_code=404, detail="Trade note not found or not owned by user")
    return db_trade_note 