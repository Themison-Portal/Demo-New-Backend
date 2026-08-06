"""
Document AI routes (Phase 4 of LLM consolidation).

Two endpoints:

- POST /chat — multi-document RAG chat. Fans out across `document_ids`,
  calls `RagClient.query()` per document, picks the BEST response (most
  sources / non-"do not contain") rather than `successes[0]`. Supports
  SSE streaming via `Accept: text/event-stream`.

- POST /retry-ingestion/{document_id} — re-runs the gRPC RAG ingestion
  pipeline for a given trial_documents row. Replaces the FE's
  `retryProcessing` -> OpenAI Vector Store path.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator, List, Optional, Tuple
from uuid import UUID, uuid4, uuid5

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.rag_client import get_rag_client
from app.config import get_settings
from app.contracts.document_ai import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    RetryIngestionResponse,
)
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.dependencies.jobs import get_job_status_service
from app.dependencies.trial_access import get_trial_with_access
from app.models.chat_messages import ChatMessage as ChatMessageRow
from app.models.chat_sessions import ChatSession
from app.models.documents import Document
from app.models.members import Member
from app.services.jobs.job_status_service import JobStatusService

logger = logging.getLogger(__name__)
router = APIRouter()

# Fixed namespace for folding a client-supplied conversation id (which may be an
# arbitrary stable string like the FE's "chat-..." id, not a UUID) into a
# deterministic chat_sessions.id. Same input string → same UUID → same row.
_CHAT_SESSION_NS = UUID("2b6d3f9e-8c4a-4b1d-9e7f-1a2b3c4d5e6f")



# ─────────────────────────────────────────
# Best-response selection (fixes the FE `successes[0]` bug)
# ─────────────────────────────────────────


_NO_INFO_RE = re.compile(
    r"(do not contain|does not contain|no information|cannot find|not found in the (provided )?(documents?|context))",
    re.IGNORECASE,
)


def _score_query_result(result: dict) -> Tuple[int, int, int, int]:
    """
    Rank a per-document query result so the best one wins the fan-out.

    Returns a tuple (high_sources, total_sources, has_info, message_length).
    Higher is better — Python tuple ordering does the comparison for us.
    """
    payload = result.get("result", {})
    sources = payload.get("sources") or []
    response_text = (payload.get("response") or "").strip()
    high = sum(1 for s in sources if str(s.get("relevance", "")).lower() == "high")
    has_info = 0 if _NO_INFO_RE.search(response_text) else 1
    return (has_info, high, len(sources), len(response_text))


def _flatten_sources(
    results: List[Tuple[Document, dict]],
) -> List[ChatSource]:
    """Merge per-doc sources into a single citation list for the FE."""
    flat: List[ChatSource] = []
    for doc, result in results:
        payload = result.get("result", {})
        for s in payload.get("sources") or []:
            flat.append(
                ChatSource(
                    file_id=str(doc.id),
                    filename=s.get("name") or doc.document_name or "",
                    section=s.get("section"),
                    page=s.get("page") if isinstance(s.get("page"), int) else None,
                    excerpt=s.get("exactText") or "",
                    relevance=s.get("relevance"),
                    bboxes=s.get("bboxes") or [],
                )
            )
    return flat


async def _fan_out_query(
    documents: List[Document],
    question: str,
    organization_id: UUID,
) -> Tuple[List[Tuple[Document, dict]], List[Tuple[Document, Exception]]]:
    """Call RAG /query for each document in parallel. Returns (successes, failures)."""
    rag = get_rag_client()

    async def _one(doc: Document) -> Tuple[Document, Optional[dict], Optional[Exception]]:
        try:
            result = await rag.query(
                query=question,
                document_id=doc.id,
                document_name=doc.document_name or "",
                organization_id=organization_id,
            )
            return doc, result, None
        except Exception as e:  # noqa: BLE001 — keep partial results
            logger.warning("RAG query failed for document %s: %s", doc.id, e)
            return doc, None, e

    results = await asyncio.gather(*[_one(d) for d in documents])
    successes = [(doc, result) for doc, result, err in results if err is None and result]
    failures = [(doc, err) for doc, _, err in results if err is not None]
    return successes, failures


# ─────────────────────────────────────────
# Endpoint: POST /chat
# ─────────────────────────────────────────


def _latest_user_question(messages: List) -> Optional[str]:
    for m in reversed(messages):
        if m.role == "user" and m.content.strip():
            return m.content.strip()
    return None


async def _load_documents_by_ids(
    db: AsyncSession,
    document_ids: List[UUID],
) -> List[Document]:
    if not document_ids:
        return []
    result = await db.execute(
        select(Document).where(Document.id.in_(document_ids))
    )
    return list(result.scalars().all())


async def _authorize_document_access(
    documents: List[Document],
    member: Member,
    db: AsyncSession,
) -> None:
    """Enforce org-isolation (and per-trial membership for non-admins) on a set
    of documents, mirroring the /api/trial-documents read endpoints.

    A document is only reachable through its trial, so we defer to
    `get_trial_with_access` on each document's `trial_id`. Fail-closed: a
    document with no trial, one in another org, or one whose trial the caller
    isn't an active member of raises 404/403 and aborts the whole request —
    rather than silently leaking or dropping it. Without this, both endpoints
    accepted any document UUID from any organization.
    """
    for doc in documents:
        if doc.trial_id is None:
            raise HTTPException(
                status_code=403,
                detail=f"Document {doc.id} is not associated with a trial you can access",
            )
        # Raises 404 (missing trial / wrong org) or 403 (not a trial member).
        await get_trial_with_access(doc.trial_id, member, db)


async def _persist_chat_turn(
    db: AsyncSession,
    member: Member,
    payload: ChatRequest,
    question: str,
    documents: List[Document],
    response: ChatResponse,
) -> None:
    """Best-effort persistence of one chat turn (the user's question + the
    assistant's answer) into `chat_sessions` / `chat_messages`, so document-AI
    conversations are retained and resumable.

    Resolves the session from `payload.session_id` (scoped to the caller) or
    creates a new one, then appends exactly this turn — not the whole message
    history the FE re-sends each call, which would duplicate. On success it sets
    `response.session_id` so the FE can continue the conversation.

    Never raises: the chat answer must reach the user even if persistence fails,
    so any error is logged and swallowed (with a rollback) rather than
    propagated. Previously this endpoint stored nothing at all.
    """
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Map the caller's session_id to a deterministic chat_sessions.id so
        # repeated turns in one conversation resolve to the same row. The FE
        # sends its per-conversation id, which may be a UUID or an arbitrary
        # stable string ("chat-..."): a real UUID is used as-is; anything else is
        # folded into a stable UUIDv5. Honouring the caller's id on create (vs a
        # fresh uuid4) is what makes append work — the FE reuses its id across
        # turns but never reads back the one we return.
        canonical_sid: Optional[UUID] = None
        if payload.session_id:
            raw = str(payload.session_id).strip()
            if raw:
                try:
                    canonical_sid = UUID(raw)
                except (ValueError, TypeError):
                    canonical_sid = uuid5(_CHAT_SESSION_NS, raw)

        session: Optional[ChatSession] = None
        if canonical_sid is not None:
            session = (
                (
                    await db.execute(
                        select(ChatSession).where(
                            ChatSession.id == canonical_sid,
                            # Scope to the caller so one user can't append to
                            # another user's session by guessing its id.
                            ChatSession.user_id == member.profile_id,
                        )
                    )
                )
                .scalars()
                .first()
            )

        if session is None:
            trial_uuid = None
            if payload.trial_id:
                try:
                    trial_uuid = UUID(str(payload.trial_id))
                except (ValueError, TypeError):
                    trial_uuid = None
            first_doc = documents[0] if documents else None
            session = ChatSession(
                id=canonical_sid or uuid4(),
                user_id=member.profile_id,
                title=(question[:60].strip() or "AI chat"),
                trial_id=trial_uuid or (first_doc.trial_id if first_doc else None),
                document_id=first_doc.id if first_doc else None,
                document_name=first_doc.document_name if first_doc else None,
                created_at=now,
                updated_at=now,
            )
            db.add(session)
            await db.flush()  # assign session.id

        db.add(
            ChatMessageRow(
                session_id=session.id,
                role="user",
                content=question,
                created_at=now,
            )
        )
        source_ids = [s.file_id for s in response.sources if s.file_id] or None
        db.add(
            ChatMessageRow(
                session_id=session.id,
                role="assistant",
                content=response.message,
                document_chunk_ids=source_ids,
                created_at=now,
            )
        )
        session.updated_at = now
        await db.commit()
        response.session_id = str(session.id)
    except Exception as e:  # never let persistence break the chat response
        await db.rollback()
        logger.warning("document-ai.chat: failed to persist chat turn: %s", e)


def _build_chat_response(
    successes: List[Tuple[Document, dict]],
    documents_queried: int,
    route: str,
    fallback_message: str,
) -> ChatResponse:
    if not successes:
        return ChatResponse(
            message=fallback_message,
            sources=[],
            route=route,
            documents_queried=documents_queried,
            documents_with_sources=0,
        )

    # Pick the best per-document result by source quality.
    best_doc, best_result = max(successes, key=lambda pair: _score_query_result(pair[1]))
    best_payload = best_result.get("result", {})
    best_text = (best_payload.get("response") or "").strip() or fallback_message

    sources = _flatten_sources(successes)
    docs_with_sources = sum(1 for _, r in successes if (r.get("result") or {}).get("sources"))

    timing = best_result.get("timing", {}) or {}
    return ChatResponse(
        message=best_text,
        sources=sources,
        route=route,
        documents_queried=documents_queried,
        documents_with_sources=docs_with_sources,
        model=None,  # RAG /query doesn't return model name today
        prompt_tokens=None,
        completion_tokens=None,
    )


async def _sse_iter(payload: ChatResponse, chunk_size: int = 40, delay_s: float = 0.01) -> AsyncIterator[bytes]:
    """
    Stream a completed `ChatResponse` as Server-Sent Events.

    The RAG service's Query RPC returns a finished answer, so this is
    chunked re-streaming rather than true token streaming — but it gives
    the UI the responsive feel of incremental rendering. When the RAG
    service grows a streaming Query (future enhancement), this iterator
    is the only place that needs to change.
    """
    def _frame(event: str, data: dict) -> bytes:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")

    yield _frame("ready", {
        "documentsQueried": payload.documents_queried,
        "documentsWithSources": payload.documents_with_sources,
        "route": payload.route,
        "model": payload.model,
        "sessionId": payload.session_id,
    })

    # Sources first so the UI can show citations as soon as they're available.
    for src in payload.sources:
        yield _frame("source", src.model_dump(by_alias=True))

    # Stream the answer text in small chunks.
    text = payload.message
    for i in range(0, len(text), chunk_size):
        yield _frame("token", {"text": text[i : i + chunk_size]})
        await asyncio.sleep(delay_s)

    yield _frame("done", {
        "promptTokens": payload.prompt_tokens,
        "completionTokens": payload.completion_tokens,
    })


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Multi-document RAG chat. Returns JSON by default; returns SSE when the
    client sends `Accept: text/event-stream`.
    """
    question = _latest_user_question(payload.messages)
    if not question:
        raise HTTPException(status_code=400, detail="No user message in `messages`")

    documents = await _load_documents_by_ids(db, payload.document_ids)

    # Org-isolation: only let the caller RAG-query documents whose trial they
    # can access. No-op when nothing loaded (guidance path below handles it).
    await _authorize_document_access(documents, member, db)

    # No selected documents -> return a guidance message rather than calling
    # a general LLM. The FE used to do an OpenAI fallback here; per the
    # Phase 4 plan, the chat endpoint always operates on indexed docs.
    if not documents:
        response = ChatResponse(
            message=(
                "No documents are selected for AI chat. Open the Document Hub, "
                "select one or more processed protocols, then ask your question again."
            ),
            sources=[],
            route="no_documents",
            documents_queried=0,
            documents_with_sources=0,
        )
    else:
        successes, failures = await _fan_out_query(documents, question,member.organization_id)
        if failures:
            logger.info(
                "document-ai.chat: %d/%d document queries failed (continuing with successes)",
                len(failures),
                len(documents),
            )
        

        response = _build_chat_response(
            successes=successes,
            documents_queried=len(documents),
            route="rag_multi" if len(documents) > 1 else "rag_single",
            fallback_message=(
                "I couldn't find an answer for that question in the selected documents. "
                "Try rephrasing or expanding the selection."
            ),
        )

    # Persist this turn (user question + assistant answer) before responding, so
    # it's captured for both the JSON and SSE paths and `response.session_id` is
    # populated for the FE. Best-effort — see `_persist_chat_turn`.
    await _persist_chat_turn(db, member, payload, question, documents, response)

    accept = (request.headers.get("accept") or "").lower()
    if "text/event-stream" in accept:
        return StreamingResponse(_sse_iter(response), media_type="text/event-stream")
    return response


# ─────────────────────────────────────────
# Endpoint: POST /retry-ingestion/{document_id}
# ─────────────────────────────────────────


@router.post("/retry-ingestion/{document_id}", response_model=RetryIngestionResponse)
async def retry_ingestion(
    document_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
    job_service: JobStatusService = Depends(get_job_status_service),
):
    """
    Re-trigger RAG ingestion for a document the user previously uploaded.

    Replaces FE `documents.retryProcessing` which hit OpenAI Vector Stores
    directly. Now the FE just calls this and the BE delegates to the RAG
    service via the existing `_run_ingestion_task` background job.
    """
    # Load the document and confirm it's reachable.
    doc = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Org-isolation: only allow reingesting a document whose trial the caller
    # can access, so a user can't trigger ingestion jobs on other orgs' docs.
    await _authorize_document_access([doc], member, db)

    if not doc.document_url:
        raise HTTPException(status_code=400, detail="Document has no stored URL to reingest from")

    # Import inline to avoid a top-level circular dep (`upload.py` imports
    # this BE app's stack heavily).
    from app.api.routes.upload import _run_ingestion_task, _set_ingestion_status

    settings = get_settings()
    job_id = await job_service.create_job(document_id)
    await _set_ingestion_status(document_id, "queued")

    redis_client = request.app.state.redis_client

    background_tasks.add_task(
        _run_ingestion_task,
        job_id=job_id,
        document_url=doc.document_url,
        document_id=document_id,
        chunk_size=750,
        redis_client=redis_client,
        use_grpc=settings.use_grpc_rag,
        grpc_address=settings.rag_service_address,
    )

    logger.info(
        "document-ai.retry-ingestion: queued job %s for document %s (member=%s)",
        job_id,
        document_id,
        member.id,
    )

    return RetryIngestionResponse(
        job_id=job_id,
        document_id=str(document_id),
        status="queued",
        message="Reingestion job queued. Poll /upload/status/{job_id} for progress.",
    )
