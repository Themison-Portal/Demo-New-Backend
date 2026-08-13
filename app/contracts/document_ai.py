"""
Contracts for the document-AI endpoints (Phase 4 of LLM consolidation).

Replaces FE `documentAIRouter.ts` direct LLM/RAG calls:
- chat              -> POST /api/document-ai/chat
- retry-processing  -> POST /api/document-ai/retry-ingestion/{document_id}

CamelCase aliasing keeps JSON shape compatible with the FE.
"""

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_camel)


# ─────────────────────────────────────────
# /api/document-ai/chat
# ─────────────────────────────────────────


class ChatMessage(_CamelModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(_CamelModel):
    messages: List[ChatMessage]
    # FE sends `coreBackendDocumentId` UUIDs (i.e., trial_documents.id values).
    # When empty, BE falls back to no-document general assistant mode.
    document_ids: List[UUID] = Field(default_factory=list)
    trial_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatSource(_CamelModel):
    file_id: str
    filename: str
    section: Optional[str] = None
    page: Optional[int] = None
    excerpt: str
    relevance: Optional[str] = None  # high/medium/low
    bboxes: List[List[float]] = Field(default_factory=list)  # docling coords for PDF highlighting


class ChatResponse(_CamelModel):
    message: str
    sources: List[ChatSource] = Field(default_factory=list)
    route: str  # "rag_multi" | "rag_single" | "no_documents" | "no_results"
    documents_queried: int
    documents_with_sources: int
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    # The chat_sessions.id this turn was persisted under. The FE should send it
    # back as `session_id` on the next request to continue the same conversation.
    session_id: Optional[str] = None


# ─────────────────────────────────────────
# /api/document-ai/retry-ingestion/{document_id}
# ─────────────────────────────────────────


class RetryIngestionResponse(_CamelModel):
    job_id: str
    document_id: str
    status: str
    message: str
