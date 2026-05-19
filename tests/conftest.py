"""
Pytest fixtures for backend unit tests.

All dependencies are mocked — no database or external services required.
"""

import os
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ.setdefault("AUTH_DISABLED", "true")

from app.main import app
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.dependencies.storage import get_storage_service
from app.dependencies.trial_access import get_trial_with_access

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_MEMBER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TEST_ORG_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TEST_PROFILE_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
TEST_TRIAL_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_scalars_result(first=None, all_items=None):
    """Build a mock db.execute() return value with .scalars().first()/.all()."""
    scalars = MagicMock()
    scalars.first.return_value = first
    scalars.all.return_value = all_items if all_items is not None else ([] if first is None else [first])
    result = MagicMock()
    result.scalars.return_value = scalars
    # Support .scalar_one() for count queries
    result.scalar_one.return_value = len(all_items) if all_items is not None else (1 if first is not None else 0)
    return result


def make_rows_result(rows=None):
    """Build a mock db.execute() return value with .all() returning tuples (for joins)."""
    result = MagicMock()
    result.all.return_value = rows or []
    result.scalars.return_value = MagicMock(
        first=MagicMock(return_value=None),
        all=MagicMock(return_value=[]),
    )
    return result


# ---------------------------------------------------------------------------
# Mock Member fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_member():
    """Admin member mock."""
    m = MagicMock()
    m.id = TEST_MEMBER_ID
    m.name = "Test Admin"
    m.email = "admin@test.com"
    m.organization_id = TEST_ORG_ID
    m.profile_id = TEST_PROFILE_ID
    m.default_role = "admin"
    m.org_role = "admin"
    m.onboarding_completed = True
    m.invited_by = None
    m.created_at = NOW
    m.updated_at = NOW
    m.first_name = "Test"
    m.last_name = "Admin"
    m.deleted_at = None
    return m


@pytest.fixture
def mock_staff_member():
    """Staff (non-admin) member mock."""
    m = MagicMock()
    m.id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    m.name = "Test Staff"
    m.email = "staff@test.com"
    m.organization_id = TEST_ORG_ID
    m.profile_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    m.default_role = "staff"
    m.org_role = "staff"
    m.onboarding_completed = True
    m.invited_by = TEST_MEMBER_ID
    m.created_at = NOW
    m.updated_at = NOW
    m.first_name = "Test"
    m.last_name = "Staff"
    m.deleted_at = None
    return m


# ---------------------------------------------------------------------------
# Mock DB session
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db():
    """Async mock DB session with common methods."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=make_scalars_result())
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Mock Storage
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_storage():
    """Mock storage service."""
    storage = MagicMock()
    storage.upload_file = MagicMock(return_value={
        "path": "uploads/test/file.pdf",
        "file_size": 1024,
    })
    storage.delete_file = MagicMock()
    return storage


# ---------------------------------------------------------------------------
# Mock Trial
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_trial():
    """Mock Trial object."""
    t = MagicMock()
    t.id = TEST_TRIAL_ID
    t.name = "Test Trial"
    t.phase = "Phase I"
    t.location = "Test Location"
    t.sponsor = "Test Sponsor"
    t.description = "A test trial"
    t.status = "active"
    t.organization_id = TEST_ORG_ID
    t.created_by = TEST_MEMBER_ID
    t.created_at = NOW
    t.updated_at = NOW
    t.image_url = None
    t.study_start = None
    t.estimated_close_out = None
    t.budget_data = None
    t.visit_schedule_template = None
    return t


# ---------------------------------------------------------------------------
# Test Clients
# ---------------------------------------------------------------------------
@pytest.fixture
def authed_client(mock_member, mock_db) -> Generator[TestClient, None, None]:
    """TestClient with admin member, mocked DB, no real dependencies."""
    app.dependency_overrides[get_current_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def staff_client(mock_staff_member, mock_db) -> Generator[TestClient, None, None]:
    """TestClient with staff member (for 403 tests)."""
    app.dependency_overrides[get_current_member] = lambda: mock_staff_member
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def trial_client(mock_member, mock_db, mock_trial) -> Generator[TestClient, None, None]:
    """TestClient that also overrides get_trial_with_access."""
    app.dependency_overrides[get_current_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_trial_with_access] = lambda: mock_trial
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def storage_client(mock_member, mock_db, mock_storage) -> Generator[TestClient, None, None]:
    """TestClient with storage service mocked."""
    app.dependency_overrides[get_current_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def trial_storage_client(mock_member, mock_db, mock_trial, mock_storage) -> Generator[TestClient, None, None]:
    """TestClient with both trial access and storage mocked."""
    app.dependency_overrides[get_current_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_trial_with_access] = lambda: mock_trial
    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Legacy fixtures (used by existing test files)
# ---------------------------------------------------------------------------
from app.dependencies.auth import get_current_user
from app.config import get_settings
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


def mock_user_override():
    return {"id": "test-user-id", "email": "test@themison.com", "auth0_sub": "auth0|test-user-id"}


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def database_url(settings):
    return settings.database_url


@pytest.fixture(scope="session")
def api_key(settings):
    return settings.upload_api_key


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_current_user] = mock_user_override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_current_user] = mock_user_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def db_session(database_url) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def test_document_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def test_organization_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content for testing"


@pytest.fixture
def mock_embedding_vectors() -> list:
    return [[0.1] * 1536 for _ in range(3)]


@pytest.fixture
def mock_docling_documents():
    from langchain_core.documents import Document
    return [
        Document(page_content="Chunk 1.", metadata={"dl_meta": {"doc_items": [{"prov": [{"page_no": 1}]}], "headings": ["Intro"]}}),
        Document(page_content="Chunk 2.", metadata={"dl_meta": {"doc_items": [{"prov": [{"page_no": 1}]}], "headings": ["Methods"]}}),
        Document(page_content="Chunk 3.", metadata={"dl_meta": {"doc_items": [{"prov": [{"page_no": 2}]}], "headings": ["Results"]}}),
    ]


@pytest.fixture
def mock_rag_ingestion_service():
    from datetime import datetime as dt
    mock_service = MagicMock()
    mock_service.ingest_pdf = AsyncMock(return_value={
        "success": True, "document_id": UUID("00000000-0000-0000-0000-000000000001"),
        "status": "ready", "chunks_count": 42, "created_at": dt.now(),
    })
    return mock_service


@pytest.fixture
def mock_rag_cache_service():
    mock_service = MagicMock()
    mock_service.invalidate_document = AsyncMock(return_value=5)
    mock_service.get_embedding = AsyncMock(return_value=None)
    mock_service.set_embedding = AsyncMock(return_value=None)
    return mock_service


@pytest.fixture
def mock_semantic_cache_service():
    mock_service = MagicMock()
    mock_service.invalidate_document = AsyncMock(return_value=3)
    mock_service.lookup = AsyncMock(return_value=None)
    mock_service.store = AsyncMock(return_value=None)
    return mock_service


@pytest.fixture
def mock_embedding_client(mock_embedding_vectors):
    mock_client = MagicMock()
    mock_client.aembed_documents = AsyncMock(return_value=mock_embedding_vectors)
    mock_client.aembed_query = AsyncMock(return_value=mock_embedding_vectors[0])
    return mock_client


@pytest.fixture
def mock_db_session():
    from unittest.mock import AsyncMock as AM, MagicMock as MM
    mock_session = MM()
    mock_session.execute = AM()
    mock_session.commit = AM()
    mock_session.rollback = AM()
    mock_session.add = MM()
    mock_session.close = AM()
    mock_result = MM()
    mock_result.rowcount = 0
    mock_session.execute.return_value = mock_result
    return mock_session


@pytest.fixture
def mock_rag_grpc_client():
    from uuid import uuid4
    mock_client = MagicMock()

    async def mock_ingest_pdf(*args, **kwargs):
        yield {"stage": "DOWNLOADING", "progress_percent": 20, "message": "Downloading...", "result": None}
        yield {"stage": "COMPLETE", "progress_percent": 100, "message": "Done!", "result": {
            "success": True, "document_id": str(uuid4()), "status": "ready",
            "chunks_count": 10, "created_at": "2024-01-01T00:00:00"}}

    mock_client.ingest_pdf = mock_ingest_pdf
    mock_client.query = AsyncMock(return_value={
        "result": {
            "response": "The inclusion criteria include patients aged 18-65 with confirmed diagnosis.",
            "sources": [
                {
                    "name": "Protocol.pdf",
                    "page": 12,
                    "section": "Inclusion Criteria",
                    "exact_text": "Patients aged 18-65 with confirmed diagnosis",
                    "bboxes": [[10.0, 20.0, 100.0, 50.0]],
                    "relevance": "HIGH",
                }
            ],
        },
        "timing": {
            "embedding_ms": 10.0,
            "retrieval_ms": 50.0,
            "generation_ms": 1000.0,
            "total_ms": 1100.0,
        },
    })
    mock_client.get_highlighted_pdf = AsyncMock(return_value=b"%PDF-1.4 highlighted")
    mock_client.invalidate_document = AsyncMock(return_value={"success": True, "chunks_deleted": 42, "cache_entries_deleted": 5})
    mock_client.health_check = AsyncMock(return_value={
        "status": "SERVING",
        "version": "0.1.0",
        "components": [
            {"name": "database", "status": "healthy"},
            {"name": "embedding", "status": "healthy"},
        ],
    })
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def sample_query_request():
    return {"query": "What are the inclusion criteria?", "document_id": "00000000-0000-0000-0000-000000000001", "document_name": "Test.pdf"}


@pytest.fixture
def sample_upload_request():
    return {"document_url": "https://storage.example.com/test.pdf", "document_id": "00000000-0000-0000-0000-000000000001", "chunk_size": 750}
