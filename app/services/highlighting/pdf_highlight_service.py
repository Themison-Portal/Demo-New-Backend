import fitz, httpx, hashlib, json

from fastapi import HTTPException
from app.services.highlighting.interfaces.pdf_highlight_service import IPDFHightlightService

class PDFHighlightService(IPDFHightlightService):
    def __init__(self, redis):
        self.redis = redis
        

    async def _get_pdf_from_url(self, url: str) -> fitz.Document:
        from app.config import get_settings
        settings = get_settings()

        # Self-healing: replace localhost/127.0.0.1 with the actual configured local_storage_base_url
        if "localhost" in url or "127.0.0.1" in url:
            import re
            base_url = settings.local_storage_base_url.rstrip("/")
            url = re.sub(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?", base_url, url)

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            pdf_bytes = resp.content
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            return pdf_doc
        

    async def get_highlighted_pdf(
        self,
        doc_url: str,
        page: int,
        bboxes: list[list[float]] | None = None,
        exact_text: str | None = None,
    ) -> bytes:
        

        # Fetch headers to check ETag / Last-Modified for cache invalidation when files change
        etag = ""
        try:
            async with httpx.AsyncClient() as client:
                resolved_url = doc_url
                if "localhost" in resolved_url or "127.0.0.1" in resolved_url:
                    import re
                    from app.config import get_settings
                    settings = get_settings()
                    base_url = settings.local_storage_base_url.rstrip("/")
                    resolved_url = re.sub(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?", base_url, resolved_url)

                head_resp = await client.head(resolved_url, follow_redirects=True)
                if head_resp.status_code == 200:
                    etag = head_resp.headers.get("etag") or head_resp.headers.get("last-modified") or ""
        except Exception:
            pass

        # 1️⃣ Build deterministic cache key
        bboxes_repr = json.dumps(bboxes or [], sort_keys=True)
        exact_text_repr = exact_text or ""
        hash_input = f"{bboxes_repr}:{exact_text_repr}"
        hash_val = hashlib.sha1(hash_input.encode()).hexdigest()[:10]
        etag_hash = hashlib.sha1(etag.encode()).hexdigest()[:8]

        cache_key = (
            f"pdf_hl_full:{hashlib.sha1(doc_url.encode()).hexdigest()[:10]}"
            f":p{page}:{hash_val}:{etag_hash}"
        )

        # 2️⃣ Redis cache (fail-safe)
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return cached
        except Exception as cache_err:
            import logging
            logging.getLogger("uvicorn").warning(f"Redis cache get failed: {cache_err}")

        # 3️⃣ Load PDF
        doc_pdf = await self._get_pdf_from_url(doc_url)

        try:
            if page < 1 or page > len(doc_pdf):
                raise ValueError(f"Page {page} out of range")

            page_obj = doc_pdf[page - 1]
            page_height = page_obj.rect.height

            # Ensure all stroke colors are set to yellow [1, 1, 0] when highlighting
            highlight_applied = False

            # 4️⃣ bboxes coordinate highlighting with bottom-left to top-left translation
            if bboxes:
                for bbox in bboxes:
                    if not bbox or len(bbox) != 4:
                        continue

                    x0, y0, x1, y1 = map(float, bbox)

                    # Docling uses BOTTOM-LEFT coordinates (y increases bottom-to-top),
                    # while fitz uses TOP-LEFT coordinates (y increases top-to-bottom).
                    # We must translate the y-coordinates: y_fitz = page_height - y_docling.
                    y0_fitz = page_height - y0
                    y1_fitz = page_height - y1

                    y0_fitz, y1_fitz = sorted([y0_fitz, y1_fitz])
                    x0_fitz, x1_fitz = sorted([x0, x1])

                    target_rect = fitz.Rect(
                        x0_fitz,
                        y0_fitz,
                        x1_fitz,
                        y1_fitz,
                    )

                    if target_rect.is_empty or target_rect.is_infinite:
                        continue

                    annot = page_obj.add_highlight_annot(target_rect)
                    annot.set_colors(stroke=[1, 1, 0])
                    annot.update()
                    highlight_applied = True

            # 5️⃣ exact_text search highlighting (precise) - fallback if bboxes not applied
            if exact_text and not highlight_applied:
                import re
                # Clean up leading/trailing quotes, smart quotes, and whitespace
                clean_text = exact_text.strip().strip('"\'“”‘’')
                clean_text = re.sub(r'\s+', ' ', clean_text)
                if clean_text:
                    matches = page_obj.search_for(clean_text)
                    
                    # Fallback 1: if clean_text is long, try the first 80 characters
                    if not matches and len(clean_text) > 100:
                        matches = page_obj.search_for(clean_text[:80])
                    
                    # Fallback 2: try the first 50 characters
                    if not matches and len(clean_text) > 50:
                        matches = page_obj.search_for(clean_text[:50])
                        
                    # Fallback 3: try the last 50 characters
                    if not matches and len(clean_text) > 50:
                        matches = page_obj.search_for(clean_text[-50:])
                    
                    if matches:
                        for rect in matches:
                            annot = page_obj.add_highlight_annot(rect)
                            annot.set_colors(stroke=[1, 1, 0])
                            annot.update()
                        highlight_applied = True

            # 6️⃣ Serialize and cache
            pdf_bytes = doc_pdf.tobytes(garbage=3, clean=True, deflate=True)
            
            # Cache the result (fail-safe)
            try:
                await self.redis.set(cache_key, pdf_bytes, ex=3600)
            except Exception as cache_err:
                import logging
                logging.getLogger("uvicorn").warning(f"Redis cache set failed: {cache_err}")

            return pdf_bytes

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error generating highlighted PDF: {str(e)}"
            )

        finally:
            doc_pdf.close()
