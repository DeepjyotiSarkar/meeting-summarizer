"""
Unique feature: semantic search / Q&A across one meeting OR every meeting
ever uploaded ("what did we decide about the Q3 budget, across all my
meetings?"). Most Meeting Summarizer clones only let you read one
transcript at a time - this turns the whole history into a searchable
knowledge base.

Chunks are embedded with OpenAI embeddings and stored in a local,
file-persisted Chroma collection (no external vector DB server needed).
If chromadb / the OpenAI key isn't available, callers should catch the
ImportError/RuntimeError and simply skip semantic search - the rest of
the app works fine without it.
"""
from typing import List, Optional
import re

import config

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils import embedding_functions

    _client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    embed_fn = embedding_functions.OpenAIEmbeddingFunction(
        api_key=config.OPENAI_API_KEY, model_name="text-embedding-3-small"
    )
    _collection = _client.get_or_create_collection(
        name="meeting_transcripts", embedding_function=embed_fn
    )
    return _collection


def _chunk_text(text: str, max_words: int = 180) -> List[str]:
    """Simple sliding window over sentences - good enough for meeting speech."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, current, count = [], [], 0
    for sent in sentences:
        words = sent.split()
        if count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sent)
        count += len(words)
    if current:
        chunks.append(" ".join(current))
    return chunks or [text]


def index_meeting(meeting_id: str, title: str, transcript_text: str) -> None:
    if not config.ENABLE_SEMANTIC_SEARCH or not transcript_text:
        return
    collection = _get_collection()
    chunks = _chunk_text(transcript_text)
    collection.add(
        ids=[f"{meeting_id}::{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[{"meeting_id": meeting_id, "title": title} for _ in chunks],
    )


def search(query: str, meeting_id: Optional[str] = None, top_k: int = 5) -> List[str]:
    if not config.ENABLE_SEMANTIC_SEARCH:
        return []
    collection = _get_collection()
    where = {"meeting_id": meeting_id} if meeting_id else None
    result = collection.query(query_texts=[query], n_results=top_k, where=where)
    docs = result.get("documents", [[]])
    return docs[0] if docs else []
