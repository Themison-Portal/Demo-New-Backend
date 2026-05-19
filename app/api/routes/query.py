"""
Query routes - RAG query via local service or gRPC.
"""
import json
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.core.openai import embedding_client
from app.config import get_settings
from app.services.doclingRag.rag_generation_service import RagGenerationService
from app.services.doclingRag.rag_retrieval_service import RagRetrievalService
from app.services.highlighting.interfaces.pdf_highlight_service import IPDFHightlightService
from app.services.highlighting.pdf_highlight_service import PDFHighlightService
from app.services.cache.rag_cache_service import RagCacheService
from app.services.cache.semantic_cache_service import SemanticCacheService
from app.dependencies.redis_client import get_redis_client
from app.dependencies.cache import get_rag_cache_service, get_semantic_cache_service

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    document_id: UUID
    document_name: str


async def _query_via_grpc(request: QueryRequest) -> dict:
    """
    Execute RAG query using gRPC RAG Service.
    """
    from app.clients.rag_client import get_rag_client

    settings = get_settings()
    client = get_rag_client()

    response = await client.query(
        query=request.query,
        document_id=request.document_id,
        document_name=request.document_name,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )

    return response


async def _query_via_local(
    request: QueryRequest,
    db: AsyncSession,
    cache_service: RagCacheService,
    semantic_cache_service: SemanticCacheService,
) -> dict:
    """
    Execute RAG query using local service.
    """
    retrieval_service = RagRetrievalService(
        db=db,
        embedding_client=embedding_client,
        cache_service=cache_service,
    )
    generation_service = RagGenerationService(
        retrieval_service=retrieval_service,
        cache_service=cache_service,
        semantic_cache_service=semantic_cache_service,
    )

    return await generation_service.generate_answer(
        query_text=request.query,
        document_id=request.document_id,
        document_name=request.document_name,
    )


def _log_timing(timing: dict, total_time: float):
    """Log comprehensive timing and cache performance summary."""
    retrieval = timing.get("retrieval", {})

    # Extract cache statuses
    embedding_hit = timing.get('embedding_cache_hit', retrieval.get('cache_hit', False))
    semantic_hit = timing.get('semantic_cache_hit', False)
    chunk_hit = retrieval.get('chunk_cache_hit', False)
    response_hit = timing.get('response_cache_hit', False)

    # Calculate time saved
    embedding_ms = timing.get('embedding_ms', retrieval.get('embedding_ms', 0))
    semantic_ms = timing.get('semantic_cache_search_ms', 0)
    llm_ms = timing.get('llm_call_ms', 0)

    TYPICAL_EMBEDDING_TIME = 500
    TYPICAL_LLM_TIME = 15000

    time_saved = 0
    if embedding_hit:
        time_saved += TYPICAL_EMBEDDING_TIME - embedding_ms
    if semantic_hit:
        time_saved += TYPICAL_LLM_TIME
    if response_hit:
        time_saved += TYPICAL_LLM_TIME

    def cache_status(hit: bool, name: str) -> str:
        return f"[HIT] {name}" if hit else f"[MISS] {name}"

    logger.info("")
    logger.info("[PERF] ============ CACHE PERFORMANCE ============")
    logger.info(f"[PERF] {cache_status(embedding_hit, 'Embedding Cache')} - {embedding_ms:.2f}ms")
    logger.info(f"[PERF] {cache_status(semantic_hit, 'Semantic Cache')} - {semantic_ms:.2f}ms" +
                (f" (similarity: {timing.get('semantic_cache_similarity', 0):.4f})" if semantic_hit else ""))
    logger.info(f"[PERF] {cache_status(chunk_hit, 'Chunk Cache')} - {retrieval.get('retrieval_total_ms', 0):.2f}ms")
    logger.info(f"[PERF] {cache_status(response_hit, 'Response Cache')} - Redis exact match")
    logger.info("[PERF] =============================================")

    cache_hits = sum([embedding_hit, semantic_hit, chunk_hit, response_hit])
    hit_rate = (cache_hits / 4) * 100

    logger.info(f"[PERF] Cache Hit Rate: {cache_hits}/4 ({hit_rate:.0f}%)")
    if time_saved > 0:
        logger.info(f"[PERF] Estimated Time Saved: ~{time_saved:.0f}ms")
    logger.info("")

    logger.info("[TIMING] ============ TIMING BREAKDOWN ============")
    logger.info(f"[TIMING] Embedding:      {embedding_ms:>8.2f}ms {'(cached)' if embedding_hit else '(computed)'}")
    if semantic_ms > 0:
        logger.info(f"[TIMING] Semantic Search:{semantic_ms:>8.2f}ms {'(HIT - skipped LLM!)' if semantic_hit else ''}")
    logger.info(f"[TIMING] Vector Search:  {retrieval.get('db_search_ms', 0):>8.2f}ms")
    logger.info(f"[TIMING] Chunks: {timing.get('original_chunk_count', 0)} -> {timing.get('compressed_chunk_count', 0)} compressed")
    if llm_ms > 0:
        logger.info(f"[TIMING] LLM (Claude):   {llm_ms:>8.2f}ms")
    logger.info("---------------------------------------------")
    logger.info(f"[TIMING] TOTAL:          {total_time:>8.2f}ms")
    logger.info("[TIMING] =============================================")


@router.post("")
async def process_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    cache_service: RagCacheService = Depends(get_rag_cache_service),
    semantic_cache_service: SemanticCacheService = Depends(get_semantic_cache_service),
    x_api_key: str = Header(...),
):
    """
    Main RAG endpoint: runs retrieval + generation.

    Uses gRPC RAG Service if USE_GRPC_RAG=true, otherwise uses local service.

    Cache hierarchy:
    1. Semantic cache (similarity >= 0.90) - for similar queries
    2. Redis response cache (exact match)
    3. Claude API call (slowest)
    """
    total_start = time.perf_counter()
    settings = get_settings()

    # Validate API key
    if not settings.upload_api_key or x_api_key != settings.upload_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info("========== QUERY START ==========")
    logger.info(f"Document ID: {request.document_id}")
    logger.info(f"Query: {request.query[:100]}{'...' if len(request.query) > 100 else ''}")

    try:
        # Route to gRPC or local service
        if settings.use_grpc_rag:
            logger.info(f"Using gRPC RAG Service at {settings.rag_service_address}")
            response = await _query_via_grpc(request)
        else:
            logger.info("Using local RAG service")
            init_start = time.perf_counter()
            response = await _query_via_local(
                request, db, cache_service, semantic_cache_service
            )
            init_time = (time.perf_counter() - init_start) * 1000
            logger.info(f"[TIMING] Service initialization: {init_time:.2f}ms")

        total_time = (time.perf_counter() - total_start) * 1000

        # Log timing
        timing = response.get("timing", {})
        _log_timing(timing, total_time)

        return response.get("result")

    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_pdf_highlight_service(
    redis=Depends(get_redis_client),
) -> IPDFHightlightService:
    return PDFHighlightService(redis)


@router.get("/highlighted-pdf")
async def get_highlighted_pdf(
    doc: str,
    page: int,
    bboxes: str | None = Query(None, description="JSON string of list of lists: [[x0,y0,x1,y1],...]"),
    pdf_service: IPDFHightlightService = Depends(get_pdf_highlight_service),
):
    """
    Get highlighted PDF page.

    Uses gRPC RAG Service if USE_GRPC_RAG=true, otherwise uses local service.
    """
    settings = get_settings()
    logger.info(f"Generating highlighted PDF for doc: {doc}, page: {page}, bboxes: {bboxes}")

    try:
        parsed_bboxes = json.loads(bboxes)
        if not isinstance(parsed_bboxes, list):
            raise ValueError("The bboxes parameter must be a JSON list.")
    except Exception:
        raise HTTPException(400, "Invalid bboxes format")

    try:
        if settings.use_grpc_rag:
            # Use gRPC service
            from app.clients.rag_client import get_rag_client

            client = get_rag_client()
            content = await client.get_highlighted_pdf(
                document_url=doc,
                page=page,
                bboxes=parsed_bboxes,
            )
        else:
            # Use local service
            content = await pdf_service.get_highlighted_pdf(doc, page, parsed_bboxes)

        return Response(content=content, media_type="application/pdf")

    except Exception as e:
        logger.error(f"Highlighted PDF error: {str(e)}")
        raise HTTPException(500, f"Error generating highlighted PDF: {str(e)}")
