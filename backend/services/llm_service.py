"""
This is the differentiating piece of the project. Instead of asking the
LLM for a loose paragraph summary (what most Meeting Summarizer clones
do), we force a single structured JSON extraction that gives us:

  - summary_text                 short prose summary
  - key_decisions[]               decisions actually made (not discussed)
  - action_items[]                {description, owner, deadline, priority}
  - risks_or_open_questions[]      unresolved items / blockers
  - sentiment                     overall tone of the meeting
  - health_score + breakdown       0-100 "how effective was this meeting"
  - follow_up_email_draft          ready-to-send recap email

Doing it in ONE call (rather than separate summary / action-item /
sentiment calls) means every field is derived from a single consistent
read of the transcript, which is both cheaper and more coherent than
chaining several prompts.

Two providers are supported and both are forced into JSON:
  - OpenAI:    response_format={"type": "json_schema", ...}
  - Anthropic: tool_choice forcing a single tool call (structured output
               pattern) rather than hoping the model wraps JSON correctly
               in prose.
"""
import json
from datetime import date
from typing import Dict, List, Optional

import config

SYSTEM_INSTRUCTIONS = """You are an expert meeting analyst. You will be given a raw \
meeting transcript. Extract a structured, ACTION-ORIENTED summary.

Rules:
- Only report decisions that were actually made, not things merely discussed.
- Only include an action item if someone is meant to DO something after the meeting.
- Assign "owner" only if a specific person is named as responsible; otherwise null.
- Assign "deadline" only if a date/timeframe was stated or clearly implied
  (e.g. "by Friday"); resolve relative dates against the meeting date given below.
  If no timeframe was given, use null - never invent one.
- priority is "high" if it blocks other work or was said urgently, else "medium",
  else "low" for nice-to-haves.
- sentiment is one of: positive, neutral, mixed, tense.
- health_score (0-100) reflects how effective the meeting was: were decisions
  reached, were action items concrete (owner+deadline), was time used well.
  Provide a breakdown with sub-scores for "decisiveness", "actionability",
  and "clarity" (each 0-100), and let health_score be a reasonable weighted
  average of those three.
- follow_up_email_draft is a short, ready-to-send recap email covering the
  decisions and action items, addressed to "Team".
- Do not hallucinate names, dates, or facts that are not in the transcript.
- Ground everything in the transcript text provided.
"""

JSON_SCHEMA = {
    "name": "meeting_summary",
    "schema": {
        "type": "object",
        "properties": {
            "summary_text": {"type": "string"},
            "key_decisions": {"type": "array", "items": {"type": "string"}},
            "risks_or_open_questions": {"type": "array", "items": {"type": "string"}},
            "sentiment": {"type": "string", "enum": ["positive", "neutral", "mixed", "tense"]},
            "health_score": {"type": "integer"},
            "health_score_breakdown": {
                "type": "object",
                "properties": {
                    "decisiveness": {"type": "integer"},
                    "actionability": {"type": "integer"},
                    "clarity": {"type": "integer"},
                },
                "required": ["decisiveness", "actionability", "clarity"],
            },
            "follow_up_email_draft": {"type": "string"},
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "owner": {"type": ["string", "null"]},
                        "deadline": {"type": ["string", "null"]},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    },
                    "required": ["description", "priority"],
                },
            },
        },
        "required": [
            "summary_text", "key_decisions", "risks_or_open_questions", "sentiment",
            "health_score", "health_score_breakdown", "follow_up_email_draft", "action_items",
        ],
    },
}


def summarize_meeting(transcript_text: str, meeting_title: str = "Untitled Meeting") -> Dict:
    user_prompt = (
        f"Meeting title: {meeting_title}\n"
        f"Meeting date: {date.today().isoformat()}\n\n"
        f"Transcript:\n{transcript_text}"
    )

    if config.LLM_PROVIDER == "anthropic":
        return _summarize_anthropic(user_prompt)
    return _summarize_openai(user_prompt)


def _summarize_openai(user_prompt: str) -> Dict:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)


def _summarize_anthropic(user_prompt: str) -> Dict:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    tool = {
        "name": "record_meeting_summary",
        "description": "Record the structured meeting summary.",
        "input_schema": JSON_SCHEMA["schema"],
    }
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4000,
        system=SYSTEM_INSTRUCTIONS,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_meeting_summary"},
        messages=[{"role": "user", "content": user_prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Anthropic did not return a tool_use block")


def answer_question(question: str, context_chunks: List[str]) -> str:
    """RAG-style Q&A over retrieved transcript chunks (see embedding_service)."""
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no matching context found)"
    prompt = (
        "Answer the user's question using ONLY the meeting excerpts below. "
        "If the answer isn't in the excerpts, say you don't have that information.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {question}"
    )

    if config.LLM_PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return resp.choices[0].message.content
