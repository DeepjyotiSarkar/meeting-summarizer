from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ActionItem
from schemas import ActionItemOut, ActionItemUpdate

router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.get("", response_model=List[ActionItemOut])
def list_action_items(status: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Unique feature: a single view of every open task across ALL meetings -
    "what do I owe people this week", without reopening each transcript.
    """
    q = db.query(ActionItem)
    if status:
        q = q.filter(ActionItem.status == status)
    return q.all()


@router.patch("/{item_id}", response_model=ActionItemOut)
def update_action_item(item_id: str, payload: ActionItemUpdate, db: Session = Depends(get_db)):
    item = db.query(ActionItem).get(item_id)
    if not item:
        raise HTTPException(404, "Action item not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item
