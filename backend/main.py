from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, engine
import models  # noqa: F401  (ensures models are registered before create_all)
from routers import meetings, action_items

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Meeting Summarizer API",
    description="Transcribes meeting audio and generates action-oriented summaries.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings.router)
app.include_router(action_items.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the plain-HTML frontend directly from the backend for a one-command demo.
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
