import datetime
import uuid

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from database import Base


def gen_id():
    return str(uuid.uuid4())


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, default="Untitled Meeting")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    audio_filename = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    status = Column(String, default="uploaded")  # uploaded -> transcribing -> summarizing -> done -> failed
    error_message = Column(Text, nullable=True)

    transcript_text = Column(Text, nullable=True)
    transcript_segments = Column(JSON, nullable=True)  # [{start, end, speaker, text}, ...]

    summary_text = Column(Text, nullable=True)
    key_decisions = Column(JSON, nullable=True)        # [str, ...]
    risks_or_open_questions = Column(JSON, nullable=True)  # [str, ...]
    sentiment = Column(String, nullable=True)           # positive/neutral/tense/mixed
    health_score = Column(Integer, nullable=True)        # 0-100
    health_score_breakdown = Column(JSON, nullable=True)
    follow_up_email_draft = Column(Text, nullable=True)

    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String, primary_key=True, default=gen_id)
    meeting_id = Column(String, ForeignKey("meetings.id"))
    description = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    deadline = Column(String, nullable=True)   # ISO date string, may be None if not mentioned
    priority = Column(String, default="medium")  # low/medium/high
    status = Column(String, default="open")      # open/done

    meeting = relationship("Meeting", back_populates="action_items")
