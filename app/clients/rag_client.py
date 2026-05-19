"""
gRPC client for RAG Service.
"""
import logging
from typing import AsyncIterator, Dict, List, Optional
from uuid import UUID

import grpc
from grpc import aio

from app.config import get_settings

# Import generated protobuf code (generated from rag-service protos via grpcio-tools)
from app.clients.generated.rag.v1.rag_service_pb2 import (
    IngestPdfRequest,
    IngestPdfProgress,
    QueryRequest,
    QueryResponse,
    GetHighlightedPdfRequest,
    HighlightedPdfResponse,
    InvalidateDocumentRequest,
    InvalidateDocumentResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    BBox,
    INGEST_STAGE_COMPLETE,
    INGEST_STAGE_ERROR,
    RELEVANCE_HIGH,
    RELEVANCE_MEDIUM,
    RELEVANCE_LOW,
)
from app.clients.generated.rag.v1.rag_service_pb2_grpc import RagServiceStub

logger = logging.getLogger(__name__)

# Relevance mapping
RELEVANCE_STR_MAP = {
    RELEVANCE_HIGH: "high",
    RELEVANCE_MEDIUM: "medium",
    RELEVANCE_LOW: "low",
}


class RagClient:
    """
    Async gRPC client for the RAG Service.
    """

    def __init__(self, address: str = None, timeout: float = None):
        settings = get_settings()
        self.address = address or settings.rag_service_address
        self.timeout = timeout or settings.rag_service_timeout
        self._channel: Optional[aio.Channel] = None
        self._stub: Optional[RagServiceStub] = None

    async def _ensure_connected(self):
        """Ensure gRPC channel is connected."""
        if self._channel is None:
            # Use secure channel for port 443 (production/cloud)
            if self.address.endswith(":443"):
                self._channel = aio.secure_channel(
                    self.address,
                    grpc.ssl_channel_credentials(),
                    options=[
                        ("grpc.max_send_message_length", 100 * 1024 * 1024),
                        ("grpc.max_receive_message_length", 100 * 1024 * 1024),
                    ],
                )
                logger.info(f"Connected to secure RAG Service at {self.address}")
            else:
                self._channel = aio.insecure_channel(
                    self.address,
                    options=[
                        ("grpc.max_send_message_length", 100 * 1024 * 1024),
                        ("grpc.max_receive_message_length", 100 * 1024 * 1024),
                    ],
                )
                logger.info(f"Connected to insecure RAG Service at {self.address}")
            self._stub = RagServiceStub(self._channel)


    async def close(self):
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Disconnected from RAG Service")

    async def ingest_pdf(
        self,
        document_url: str,
        document_id: UUID,
        chunk_size: int = 750,
    ) -> AsyncIterator[Dict]:
        """
        Ingest PDF with streaming progress updates.

        Yields:
            Dict with stage, progress_percent, message, and optional result.
        """
        await self._ensure_connected()

        request = IngestPdfRequest(
            document_url=document_url,
            document_id=str(document_id),
            chunk_size=chunk_size,
        )

        try:
            async for progress in self._stub.IngestPdf(request, timeout=self.timeout):
                yield {
                    "stage": progress.stage,
                    "progress_percent": progress.progress_percent,
                    "message": progress.message,
                    "result": self._parse_ingest_result(progress.result)
                    if progress.stage in (INGEST_STAGE_COMPLETE, INGEST_STAGE_ERROR)
                    else None,
                }
        except grpc.RpcError as e:
            logger.error(f"IngestPdf RPC error: {e}")
            raise RuntimeError(f"RAG Service error: {e.details()}")

    def _parse_ingest_result(self, result) -> Dict:
        """Parse IngestResult protobuf to dict."""
        return {
            "success": result.success,
            "document_id": result.document_id,
            "status": result.status,
            "chunks_count": result.chunks_count,
            "created_at": result.created_at,
            "error": result.error if result.error else None,
        }

    async def query(
        self,
        query: str,
        document_id: UUID,
        document_name: str,
        top_k: int = 20,
        min_score: float = 0.04,
    ) -> Dict:
        """
        Execute RAG query.

        Returns:
            Dict with answer, timing, and cache_info.
        """
        await self._ensure_connected()

        request = QueryRequest(
            query=query,
            document_id=str(document_id),
            document_name=document_name,
            top_k=top_k,
            min_score=min_score,
        )

        try:
            response: QueryResponse = await self._stub.Query(request, timeout=self.timeout)
            return self._parse_query_response(response)
        except grpc.RpcError as e:
            logger.error(f"Query RPC error: {e}")
            raise RuntimeError(f"RAG Service error: {e.details()}")

    def _parse_query_response(self, response: QueryResponse) -> Dict:
        """Parse QueryResponse protobuf to dict."""
        # Parse sources
        sources = []
        for source in response.answer.sources:
            bboxes = [
                [bbox.x0, bbox.y0, bbox.x1, bbox.y1]
                for bbox in source.bboxes
            ]
            sources.append({
                "name": source.name,
                "page": source.page,
                "section": source.section if source.section else None,
                "exactText": source.exact_text,
                "bboxes": bboxes,
                "relevance": RELEVANCE_STR_MAP.get(source.relevance, "high"),
            })

        return {
            "result": {
                "response": response.answer.response,
                "sources": sources,
            },
            "timing": {
                "embedding_ms": response.timing.embedding_ms,
                "retrieval_total_ms": response.timing.retrieval_ms,
                "llm_call_ms": response.timing.generation_ms,
                "generation_total_ms": response.timing.total_ms,
                "original_chunk_count": response.timing.chunks_retrieved,
                "compressed_chunk_count": response.timing.chunks_compressed,
                "embedding_cache_hit": response.cache_info.embedding_cache_hit,
                "semantic_cache_hit": response.cache_info.semantic_cache_hit,
                "chunk_cache_hit": response.cache_info.chunk_cache_hit,
                "response_cache_hit": response.cache_info.response_cache_hit,
                "semantic_cache_similarity": response.cache_info.semantic_similarity,
            },
        }

    async def get_highlighted_pdf(
        self,
        document_url: str,
        page: int,
        bboxes: List[List[float]],
    ) -> bytes:
        """
        Get highlighted PDF page.

        Returns:
            PDF bytes with highlights.
        """
        await self._ensure_connected()

        pb_bboxes = [
            BBox(x0=b[0], y0=b[1], x1=b[2], y1=b[3])
            for b in bboxes
            if len(b) == 4
        ]

        request = GetHighlightedPdfRequest(
            document_url=document_url,
            page=page,
            bboxes=pb_bboxes,
        )

        try:
            response: HighlightedPdfResponse = await self._stub.GetHighlightedPdf(request, timeout=self.timeout)
            return response.pdf_content
        except grpc.RpcError as e:
            logger.error(f"GetHighlightedPdf RPC error: {e}")
            raise RuntimeError(f"RAG Service error: {e.details()}")

    async def invalidate_document(self, document_id: UUID) -> Dict:
        """
        Invalidate cache for a document.

        Returns:
            Dict with success, chunks_deleted, cache_entries_deleted.
        """
        await self._ensure_connected()

        request = InvalidateDocumentRequest(document_id=str(document_id))

        try:
            response: InvalidateDocumentResponse = await self._stub.InvalidateDocument(request, timeout=self.timeout)
            return {
                "success": response.success,
                "chunks_deleted": response.chunks_deleted,
                "cache_entries_deleted": response.cache_entries_deleted,
            }
        except grpc.RpcError as e:
            logger.error(f"InvalidateDocument RPC error: {e}")
            raise RuntimeError(f"RAG Service error: {e.details()}")

    async def health_check(self) -> Dict:
        """
        Check RAG Service health.

        Returns:
            Dict with status, version, and components.
        """
        await self._ensure_connected()

        request = HealthCheckRequest()

        try:
            response: HealthCheckResponse = await self._stub.HealthCheck(request, timeout=self.timeout)
            return {
                "status": response.status,
                "version": response.version,
                "components": [
                    {
                        "name": c.name,
                        "healthy": c.healthy,
                        "message": c.message,
                    }
                    for c in response.components
                ],
            }
        except grpc.RpcError as e:
            logger.error(f"HealthCheck RPC error: {e}")
            return {
                "status": "NOT_SERVING",
                "version": "unknown",
                "components": [],
                "error": str(e),
            }


# Singleton instance
_rag_client: Optional[RagClient] = None


def get_rag_client() -> RagClient:
    """Get the RAG client singleton."""
    global _rag_client
    if _rag_client is None:
        _rag_client = RagClient()
    return _rag_client


async def close_rag_client():
    """Close the RAG client connection."""
    global _rag_client
    if _rag_client:
        await _rag_client.close()
        _rag_client = None
