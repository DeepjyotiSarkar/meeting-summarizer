# Meeting Summarizer

Transcribe meeting audio and turn it into decisions, owned action items,
calendar reminders, and a searchable memory of every meeting you've ever
recorded — not just a wall of text.

## What makes this different

Most "meeting summarizer" projects stop at *transcript → paragraph
summary*. This one treats the summary as **structured data**, which is
what unlocks everything else:

| Feature | Why it's not just another clone |
|---|---|
| **Single-pass structured extraction** | One forced-JSON LLM call returns summary, decisions, action items (with owner/deadline/priority), risks, sentiment, and a health score together — consistent, cheap, and auditable (see `backend/services/llm_service.py`). |
| **Meeting Health Score** | A 0–100 score with a *decisiveness / actionability / clarity* breakdown, so you can tell a productive meeting from a rambling one at a glance. |
| **Action items become calendar events** | One click exports a `.ics` file — deadlines actually land on a calendar instead of dying in a text box. |
| **Cross-meeting task dashboard** | Every open action item, from every meeting, in one view — "what do I owe people this week." |
| **"Ask your meetings" (RAG)** | Semantic search over one meeting *or every meeting you've ever uploaded*, via embeddings + a local vector store — turns your meeting history into a knowledge base, not an archive. |
| **Auto-generated minutes.docx + follow-up email** | Two artifacts people actually forward, generated for free alongside the summary. |
| **Provider-agnostic** | ASR: OpenAI Whisper API *or* free/offline `faster-whisper`. LLM: OpenAI *or* Anthropic. Swap via one `.env` line — nothing else changes. |

## Architecture

```
 ┌──────────┐   upload audio    ┌────────────────────┐
 │ Frontend │ ────────────────▶ │   FastAPI backend    │
 │ (vanilla │                   │                      │
 │  HTML/JS)│ ◀──── poll ─────  │  1. ASR  (asr_service)│──▶ transcript + segments
 └──────────┘   status/result   │  2. LLM  (llm_service)│──▶ structured summary JSON
                                 │  3. persist (SQLite)  │
                                 │  4. index (chroma)    │──▶ semantic search
                                 └──────────┬───────────┘
                                            │
                         ┌──────────────────┼───────────────────┐
                         ▼                  ▼                   ▼
                  GET /meetings/:id   /calendar.ics       /minutes.docx
                  (poll while         (action items       (python-docx
                   processing)         → calendar)          minutes doc)
```

Processing runs as a FastAPI `BackgroundTask` so the upload request
returns immediately; the frontend polls `GET /meetings/{id}` and renders
live status (`uploaded → transcribing → summarizing → done`).

### Project layout

```
backend/
  main.py                 FastAPI app, mounts routers + serves the frontend
  config.py                all env-driven settings in one place
  database.py, models.py   SQLAlchemy (Meeting, ActionItem)
  schemas.py                Pydantic response/request models
  services/
    asr_service.py          OpenAI Whisper API  |  faster-whisper (local)
    llm_service.py           structured JSON summarization + Q&A (the core logic)
    embedding_service.py     chunk + embed + search transcripts (chromadb)
    calendar_service.py      action items -> .ics
    docx_service.py          meeting -> minutes.docx
  routers/
    meetings.py              upload, get, list, exports, /ask
    action_items.py          cross-meeting task dashboard, status updates
frontend/
  index.html, style.css, app.js   single-page app, no build step
demo/
  DEMO_SCRIPT.md             shot list for the demo video deliverable
```

## Prompt design (evaluation focus: "LLM prompt effectiveness")

The summarization prompt (`SYSTEM_INSTRUCTIONS` in `llm_service.py`) is
deliberately constrained rather than open-ended:

- **Decisions vs. discussion** — explicitly told to only report things
  that were *decided*, not everything that was *discussed*. This is the
  single biggest quality difference between a useful summary and a
  generic one.
- **No hallucinated owners/deadlines** — the model is told to use
  `null` rather than invent a name or date, and deadlines are resolved
  against the actual meeting date passed in the prompt.
- **Forced JSON, not parsed prose** — OpenAI calls use
  `response_format={"type": "json_schema", ...}`; Anthropic calls use
  `tool_choice` to force a single tool call. Neither relies on asking
  the model nicely to "return JSON" and hoping — this eliminates an
  entire class of parsing failures common in naive implementations.
- **One call, not a chain** — decisions, action items, sentiment, and
  the health score are all derived from a single read of the transcript,
  so they can't contradict each other the way outputs from independent
  prompts sometimes do.

## Setup

### 1. Prerequisites
- Python 3.11+
- `ffmpeg` on your PATH (needed for audio decoding)
- An OpenAI and/or Anthropic API key

### 2. Configure
```bash
cp .env.example .env
# edit .env — at minimum set OPENAI_API_KEY (default provider for both ASR + LLM)
```

### 3. Run locally
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Open **http://localhost:8000** — the backend serves the frontend directly,
so there's nothing else to start.

### 4. Or run with Docker
```bash
docker compose up --build
```

### 5. Try it
Upload a short audio file from the sidebar. Watch the status move through
`transcribing → summarizing → done`, then explore the health score,
action items, calendar export, minutes export, and the "Ask" box.

## Configuration reference (`.env`)

| Variable | Values | Notes |
|---|---|---|
| `ASR_PROVIDER` | `openai` \| `local` | `local` uses `faster-whisper`, no API key, slower, needs ffmpeg |
| `LLM_PROVIDER` | `openai` \| `anthropic` | swaps the summarization + Q&A backend |
| `ENABLE_SEMANTIC_SEARCH` | `true` \| `false` | disable to skip the `chromadb` dependency entirely |
| `ENABLE_CALENDAR_EXPORT` | `true` \| `false` | |
| `ENABLE_DOCX_EXPORT` | `true` \| `false` | |

## API reference (quick)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/meetings/upload` | multipart upload (`file`, `title`) — starts processing |
| `GET` | `/meetings` | list all meetings |
| `GET` | `/meetings/{id}` | full detail (poll this while processing) |
| `GET` | `/meetings/{id}/calendar.ics` | download action items as calendar events |
| `GET` | `/meetings/{id}/minutes.docx` | download formatted minutes |
| `POST` | `/meetings/ask` | `{question, meeting_id?}` — RAG Q&A, omit `meeting_id` to search everything |
| `GET` | `/action-items?status=open` | cross-meeting task dashboard |
| `PATCH` | `/action-items/{id}` | update status/owner/deadline/priority |

Interactive docs (from FastAPI) are auto-generated at **`/docs`**.

## Evaluating this project

Mapped to the stated evaluation focus:

- **Transcription accuracy** — pluggable ASR (`ASR_PROVIDER`) so accuracy
  can be compared between Whisper API and local models on the same audio.
- **Summary quality** — see "Prompt design" above; decisions/action
  items are grounded and structured, not freeform.
- **LLM prompt effectiveness** — single forced-JSON extraction with an
  explicit schema (`JSON_SCHEMA` in `llm_service.py`), swappable across
  two model providers with no logic changes elsewhere.
- **Code structure** — clear separation of `services/` (business logic,
  swappable per feature), `routers/` (HTTP layer), and `models`/`schemas`
  (data), so any one piece (e.g. the ASR backend) can be swapped without
  touching the rest.

## Extending further
- **Speaker diarization**: `asr_service.py` is the place to plug in
  `pyannote.audio` or the diarization output some ASR APIs return, and
  attach a `speaker` field to each segment — `llm_service.py`'s prompt
  can then be told to reason per-speaker (e.g. talk-time balance as a
  4th health-score component).
- **Slack/email delivery**: the follow-up email draft is already
  generated — wiring it to an SMTP or Slack webhook call in
  `routers/meetings.py` after `_process_meeting` finishes is a small
  addition.
- **Live/streaming transcription**: swap the upload flow for a
  WebSocket endpoint and a streaming-capable ASR provider.
