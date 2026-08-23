"""
Central configuration, loaded from environment variables (.env).
Keeping every tunable in one place is what lets the rest of the
codebase stay provider-agnostic (swap Whisper<->local ASR, or
OpenAI<->Anthropic for the LLM, without touching business logic).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'meetings.db'}")

# --- ASR ---
# "openai"  -> Whisper API (openai-whisper-1), needs OPENAI_API_KEY
# "local"   -> faster-whisper running on this machine, free, no key, slower
ASR_PROVIDER = os.getenv("ASR_PROVIDER", "openai")
LOCAL_WHISPER_MODEL_SIZE = os.getenv("LOCAL_WHISPER_MODEL_SIZE", "base")

# --- LLM ---
# "openai"    -> gpt-4o-mini / gpt-4o, needs OPENAI_API_KEY
# "anthropic" -> claude-sonnet-4-6, needs ANTHROPIC_API_KEY
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Optional features (each degrades gracefully if disabled/missing deps) ---
ENABLE_SEMANTIC_SEARCH = os.getenv("ENABLE_SEMANTIC_SEARCH", "true").lower() == "true"
ENABLE_CALENDAR_EXPORT = os.getenv("ENABLE_CALENDAR_EXPORT", "true").lower() == "true"
ENABLE_DOCX_EXPORT = os.getenv("ENABLE_DOCX_EXPORT", "true").lower() == "true"

CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_store")
