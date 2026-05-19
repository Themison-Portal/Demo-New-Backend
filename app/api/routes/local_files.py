"""
Serves files stored by ``LocalStorageService`` from the ``./uploads/`` directory.

Mounted at ``/local-files`` so that URLs returned by the local storage backend
(e.g. ``http://localhost:8000/local-files/trials/<id>/file.pdf``) resolve to
actual file responses — the same way GCS signed URLs would.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

UPLOADS_ROOT = Path("uploads").resolve()


@router.get("/{file_path:path}")
async def serve_local_file(file_path: str):
    target = (UPLOADS_ROOT / file_path).resolve()

    # Path-traversal protection
    if not str(target).startswith(str(UPLOADS_ROOT)):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(target)
