"""
Serves files stored by ``LocalStorageService`` from the ``./uploads/`` directory.

Mounted at ``/local-files`` so that URLs returned by the local storage backend
(e.g. ``http://localhost:8000/local-files/trials/<id>/file.pdf``) resolve to
actual file responses — the same way GCS signed URLs would.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db

router = APIRouter()

UPLOADS_ROOT = Path("uploads").resolve()


@router.get("/{file_path:path}")
async def serve_local_file(file_path: str, db: AsyncSession = Depends(get_db)):
    target = (UPLOADS_ROOT / file_path).resolve()

    # Path-traversal protection
    if not str(target).startswith(str(UPLOADS_ROOT)):
        raise HTTPException(status_code=403, detail="Forbidden")

    if target.is_file():
        return FileResponse(target)

    # The on-disk copy is gone (Render wipes the ephemeral /app/uploads disk on
    # every redeploy/restart). Fall back to the durable Postgres blob stored at
    # upload time, keyed by the same relative path.
    row = (
        await db.execute(
            text(
                "SELECT content, content_type FROM document_blobs WHERE rel_path = :p"
            ),
            {"p": file_path},
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")

    content, content_type = row
    return Response(
        content=bytes(content),
        media_type=content_type or "application/octet-stream",
    )
