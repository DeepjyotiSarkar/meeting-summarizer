import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session

import config
from database import get_db
from models import Meeting, ActionItem
from schemas import MeetingOut, MeetingListItem, AskRequest
from services import asr_service, llm_service, calendar_service, embedding_service

router = APIRouter(prefix="/meetings", tags=["meetings"])

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg", ".flac"}


@router.post("/upload", response_model=MeetingOut)
def upload_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form("Untitled Meeting"),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    meeting = Meeting(title=title, status="uploaded")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    dest = config.UPLOAD_DIR / f"{meeting.id}{ext}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    meeting.audio_filename = dest.name
    db.commit()

    background_tasks.add_task(_process_meeting, meeting.id, str(dest))
    return meeting


def _process_meeting(meeting_id: str, audio_path: str):
    """Runs off the request thread: ASR -> LLM extraction -> persist -> index."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        meeting = db.query(Meeting).get(meeting_id)
        meeting.status = "transcribing"
        db.commit()

        full_text, segments = asr_service.transcribe(audio_path)
        meeting.transcript_text = full_text
        meeting.transcript_segments = segments
        if segments:
            meeting.duration_seconds = segments[-1].get("end", 0)
        meeting.status = "summarizing"
        db.commit()

        summary = llm_service.summarize_meeting(full_text, meeting.title)
        meeting.summary_text = summary["summary_text"]
        meeting.key_decisions = summary["key_decisions"]
        meeting.risks_or_open_questions = summary["risks_or_open_questions"]
        meeting.sentiment = summary["sentiment"]
        meeting.health_score = summary["health_score"]
        meeting.health_score_breakdown = summary["health_score_breakdown"]
        meeting.follow_up_email_draft = summary["follow_up_email_draft"]

        for ai in summary.get("action_items", []):
            db.add(ActionItem(
                meeting_id=meeting.id,
                description=ai["description"],
                owner=ai.get("owner"),
                deadline=ai.get("deadline"),
                priority=ai.get("priority", "medium"),
            ))

        meeting.status = "done"
        db.commit()

        try:
            embedding_service.index_meeting(meeting.id, meeting.title, full_text)
        except Exception:
            pass  # semantic search is a bonus feature, never fail the pipeline over it

    except Exception as e:  # noqa: BLE001
        meeting = db.query(Meeting).get(meeting_id)
        meeting.status = "failed"
        meeting.error_message = str(e)
        db.commit()
    finally:
        db.close()


@router.get("", response_model=List[MeetingListItem])
def list_meetings(db: Session = Depends(get_db)):
    return db.query(Meeting).order_by(Meeting.created_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).get(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return meeting


@router.get("/{meeting_id}/calendar.ics")
def export_calendar(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).get(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    ics = calendar_service.build_ics(meeting.title, meeting.action_items)
    return PlainTextResponse(
        ics,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{meeting.title}.ics"'},
    )


@router.get("/{meeting_id}/minutes.docx")
def export_minutes(meeting_id: str, db: Session = Depends(get_db)):
    if not config.ENABLE_DOCX_EXPORT:
        raise HTTPException(400, "DOCX export disabled")
    from services.docx_service import build_minutes_docx

    meeting = db.query(Meeting).get(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    buf = build_minutes_docx(meeting)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{meeting.title}_minutes.docx"'},
    )


@router.post("/ask")
def ask_question(payload: AskRequest):
    """Semantic Q&A over one meeting, or across every meeting ever uploaded."""
    chunks = embedding_service.search(payload.question, meeting_id=payload.meeting_id)
    answer = llm_service.answer_question(payload.question, chunks)
    return {"answer": answer, "sources_used": len(chunks)}
