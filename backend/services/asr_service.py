"""
Transcription layer. Two interchangeable backends so the project isn't
locked into a paid API:

  ASR_PROVIDER=openai  -> OpenAI Whisper API (best accuracy, costs money)
  ASR_PROVIDER=local   -> faster-whisper running on-device (free, offline)

Both return the same shape: (full_text, segments) where each segment is
{start, end, text} in seconds. This normalized shape is what lets the
rest of the app (health score, calendar export, semantic search) stay
provider-agnostic.
"""
from typing import List, Dict, Tuple

import config


def transcribe(audio_path: str) -> Tuple[str, List[Dict]]:
    if config.ASR_PROVIDER == "local":
        return _transcribe_local(audio_path)
    return _transcribe_openai(audio_path)


def _transcribe_openai(audio_path: str) -> Tuple[str, List[Dict]]:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = [
        {"start": s.start, "end": s.end, "text": s.text.strip()}
        for s in getattr(result, "segments", []) or []
    ]
    full_text = result.text.strip()
    if not segments and full_text:
        # Some SDK versions omit segments; fall back to one big segment.
        segments = [{"start": 0.0, "end": 0.0, "text": full_text}]
    return full_text, segments


def _transcribe_local(audio_path: str) -> Tuple[str, List[Dict]]:
    """
    Free/offline fallback using faster-whisper.
    pip install faster-whisper (needs ffmpeg on PATH).
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(config.LOCAL_WHISPER_MODEL_SIZE, compute_type="int8")
    segments_iter, _info = model.transcribe(audio_path, vad_filter=True)

    segments = []
    full_text_parts = []
    for seg in segments_iter:
        text = seg.text.strip()
        segments.append({"start": seg.start, "end": seg.end, "text": text})
        full_text_parts.append(text)

    return " ".join(full_text_parts), segments
