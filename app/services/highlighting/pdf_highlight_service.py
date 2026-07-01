import fitz, httpx, hashlib, json

from fastapi import HTTPException
from app.services.highlighting.interfaces.pdf_highlight_service import IPDFHightlightService

class PDFHighlightService(IPDFHightlightService):
    def __init__(self, redis):
        self.redis = redis
        

    async def _get_pdf_from_url(self, url: str) -> fitz.Document:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
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
        

        # 1️⃣ Build deterministic cache key
        bboxes_repr = json.dumps(bboxes or [], sort_keys=True)
        exact_text_repr = exact_text or ""
        hash_input = f"{bboxes_repr}:{exact_text_repr}"
        hash_val = hashlib.sha1(hash_input.encode()).hexdigest()[:10]

        cache_key = (
            f"pdf_hl:{hashlib.sha1(doc_url.encode()).hexdigest()[:10]}"
            f":p{page}:{hash_val}"
        )

        # 2️⃣ Redis cache
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        # 3️⃣ Load PDF
        doc_pdf = await self._get_pdf_from_url(doc_url)

        try:
            if page < 1 or page > len(doc_pdf):
                raise ValueError(f"Page {page} out of range")

            page_obj = doc_pdf[page - 1]
            page_height = page_obj.rect.height

            highlight_applied = False

            # 4️⃣ exact_text search highlighting (precise)
            if exact_text:
                import re
                clean_text = re.sub(r'\s+', ' ', exact_text.strip())
                if clean_text:
                    matches = page_obj.search_for(clean_text)
                    # Fallback for longer query results: search for first 80 chars
                    if not matches and len(clean_text) > 100:
                        matches = page_obj.search_for(clean_text[:80])
                    
                    if matches:
                        for rect in matches:
                            annot = page_obj.add_highlight_annot(rect)
                            annot.update()
                        highlight_applied = True

            # 5️⃣ bboxes coordinate highlighting with bottom-left to top-left translation
            if bboxes:
                for bbox in bboxes:
                    if not bbox or len(bbox) != 4:
                        continue

                    x0, y0, x1, y1 = map(float, bbox)

                    # Docling coordinates are BOTTOM-LEFT (y increases bottom-to-top).
                    # fitz coordinates are TOP-LEFT (y increases top-to-bottom).
                    y0_fitz, y1_fitz = sorted([page_height - y0, page_height - y1])
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
                    annot.update()
                    highlight_applied = True

            # 6️⃣ Serialize and cache
            pdf_bytes = doc_pdf.tobytes(garbage=3, clean=True, deflate=True)
            await self.redis.set(cache_key, pdf_bytes, ex=3600)

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
