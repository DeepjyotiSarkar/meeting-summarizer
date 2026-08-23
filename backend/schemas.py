from typing import List, Optional
from pydantic import BaseModel


class ActionItemOut(BaseModel):
    id: str
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "medium"
    status: str = "open"

    class Config:
        from_attributes = True


class ActionItemUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None


class MeetingOut(BaseModel):
    id: str
    title: str
    status: str
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    transcript_text: Optional[str] = None
    summary_text: Optional[str] = None
    key_decisions: Optional[List[str]] = None
    risks_or_open_questions: Optional[List[str]] = None
    sentiment: Optional[str] = None
    health_score: Optional[int] = None
    health_score_breakdown: Optional[dict] = None
    follow_up_email_draft: Optional[str] = None
    action_items: List[ActionItemOut] = []

    class Config:
        from_attributes = True


class MeetingListItem(BaseModel):
    id: str
    title: str
    status: str
    health_score: Optional[int] = None

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    question: str
    meeting_id: Optional[str] = None  # None => search across ALL meetings
