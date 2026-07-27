"""
HTTP client for the RAG service.

Public interface is intentionally identical to `RagClient` (the gRPC client)
so that the factory in `get_rag_client()` can swap transports without any
call-site changes. Return shapes match the gRPC client's exactly.
"""
import json
import logging
from typing import AsyncIterator, Dict, List, Optional
from uuid import UUID

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class RagHttpClient:
    """Async HTTP client for the RAG Service."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        settings = get_settings()
        raw = base_url or settings.rag_service_address
        self.base_url = self._normalize_base_url(raw)
        self.timeout = timeout or settings.rag_service_timeout
        self._client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        """
        Accept both bare `host:port` (legacy gRPC form) and `https?://host`
        URLs. A bare host:port without scheme defaults to http://. Strip any
        trailing slash so endpoint joins are unambiguous.
        """
        s = raw.strip().rstrip("/")
        if s.startswith("http://") or s.startswith("https://"):
            return s
        # If the user left the legacy `:443` gRPC suffix, prefer https.
        if s.endswith(":443"):
            return f"https://{s[:-4]}"
        return f"http://{s}"

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
            logger.info(f"RAG HTTP client → {self.base_url}")
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ingest_pdf(
        self,
        document_url: str,
        document_id: UUID,
        organization_id: UUID,
        chunk_size: int = 750,
    ) -> AsyncIterator[Dict]:
        """Stream ingestion progress events from the HTTP SSE endpoint."""
        client = await self._ensure_client()
        body = {
            "document_url": document_url,
            "document_id": str(document_id),
            "organization_id": str(organization_id),
            "chunk_size": chunk_size,
        }
        try:
            async with client.stream(
                "POST",
                "/v1/ingest_pdf",
                json=body,
                timeout=self.timeout,
            ) as resp:
                if resp.status_code >= 400:
                    text = await resp.aread()
                    raise RuntimeError(
                        f"RAG /ingest_pdf HTTP {resp.status_code}: {text!r}"
                    )
                async for raw_line in resp.aiter_lines():
                    if not raw_line:
                        continue
                    if not raw_line.startswith("data:"):
                        continue
                    payload = raw_line[5:].strip()
                    if not payload:
                        continue
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        logger.warning(f"Bad SSE payload: {payload!r}")
                        continue
                    yield event
        except httpx.HTTPError as e:
            logger.error(f"ingest_pdf HTTP error: {e}")
            raise RuntimeError(f"RAG Service error: {e}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        model_hint: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_schema: Optional[Dict] = None,
        response_schema_name: str = "structured_output",
        feature_tag: str = "",
    ) -> Dict:
        client = await self._ensure_client()
        body = {
            "messages": messages,
            "model_hint": model_hint or "",
            "temperature": float(temperature) if temperature else 0.0,
            "max_tokens": int(max_tokens) if max_tokens else 0,
            "feature_tag": feature_tag or "",
            "response_schema_json": json.dumps(response_schema) if response_schema else "",
            "response_schema_name": response_schema_name or "",
        }
        try:
            resp = await client.post("/v1/generate", json=body, timeout=self.timeout)
        except httpx.HTTPError as e:
            logger.error(f"generate HTTP error (feature={feature_tag}): {e}")
            raise RuntimeError(f"RAG Service Generate error: {e}")
        if resp.status_code >= 400:
            raise RuntimeError(
                f"RAG Service Generate error: HTTP {resp.status_code} {resp.text}"
            )
        data = resp.json()
        return {
            "content": data.get("content", ""),
            "model": data.get("model", ""),
            "prompt_tokens": data.get("prompt_tokens", 0),
            "completion_tokens": data.get("completion_tokens", 0),
        }

    async def query(
        self,
        query: str,
        document_id: UUID,
        document_name: str,
        organization_id: UUID,
        top_k: int = 20,
        min_score: float = 0.04,
    ) -> Dict:
        client = await self._ensure_client()
        body = {
            "query": query,
            "document_id": str(document_id),
            "document_name": document_name,
            "organization_id": str(organization_id),
            "top_k": top_k,
            "min_score": min_score,
        }
        try:
            resp = await client.post("/v1/query", json=body, timeout=self.timeout)
        except httpx.HTTPError as e:
            logger.error(f"query HTTP error: {e}")
            raise RuntimeError(f"RAG Service error: {e}")
        if resp.status_code >= 400:
            raise RuntimeError(
                f"RAG Service error: HTTP {resp.status_code} {resp.text}"
            )
        return resp.json()

    async def get_highlighted_pdf(
        self,
        document_url: str,
        page: int,
        bboxes: List[List[float]],
    ) -> bytes:
        client = await self._ensure_client()
        body = {
            "document_url": document_url,
            "page": page,
            "bboxes": [
                {"x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3]}
                for b in bboxes
                if len(b) == 4
            ],
        }
        try:
            resp = await client.post(
                "/v1/get_highlighted_pdf", json=body, timeout=self.timeout
            )
        except httpx.HTTPError as e:
            logger.error(f"get_highlighted_pdf HTTP error: {e}")
            raise RuntimeError(f"RAG Service error: {e}")
        if resp.status_code >= 400:
            raise RuntimeError(
                f"RAG Service error: HTTP {resp.status_code} {resp.text}"
            )
        return resp.content

    async def invalidate_document(self, document_id: UUID,organization_id: UUID) -> Dict:
        client = await self._ensure_client()
        try:
            resp = await client.post(
                "/v1/invalidate_document",
                json={"document_id": str(document_id),"organization_id": str(organization_id)},
                timeout=self.timeout,
            )
        except httpx.HTTPError as e:
            logger.error(f"invalidate_document HTTP error: {e}")
            raise RuntimeError(f"RAG Service error: {e}")
        if resp.status_code >= 400:
            raise RuntimeError(
                f"RAG Service error: HTTP {resp.status_code} {resp.text}"
            )
        data = resp.json()
        return {
            "success": data.get("success", False),
            "chunks_deleted": data.get("chunks_deleted", 0),
            "cache_entries_deleted": data.get("cache_entries_deleted", 0),
        }

    async def health_check(self) -> Dict:
        client = await self._ensure_client()
        try:
            resp = await client.get("/healthz", timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"health_check HTTP error: {e}")
            return {
                "status": "NOT_SERVING",
                "version": "unknown",
                "components": [],
                "error": str(e),
            }
