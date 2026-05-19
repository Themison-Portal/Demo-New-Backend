"""
Live integration tests against the deployed Cloud Run instance.

These tests hit the real API + real Supabase DB. They're skipped unless the
required env vars are set, so regular `pytest` runs stay green.

Required env vars:
    CLOUD_BASE_URL      e.g. https://core-backend-eu-XXXXXXXX.europe-west1.run.app
    CLOUD_AUTH_TOKEN    a valid Auth0 JWT (Bearer token without the "Bearer " prefix)
    CLOUD_TRIAL_ID      UUID of a real trial the caller has access to
    CLOUD_DOCUMENT_ID   UUID of a real document

Run only these tests:
    pytest tests/test_chat_sessions_cloud.py -v

Run everything except cloud:
    pytest -m "not cloud"
"""

import os
import uuid
from typing import Generator, List

import httpx
import pytest


BASE_URL = os.getenv("CLOUD_BASE_URL")
AUTH_TOKEN = os.getenv("CLOUD_AUTH_TOKEN")
TRIAL_ID = os.getenv("CLOUD_TRIAL_ID")
DOCUMENT_ID = os.getenv("CLOUD_DOCUMENT_ID")

_missing = [
    name
    for name, val in [
        ("CLOUD_BASE_URL", BASE_URL),
        ("CLOUD_AUTH_TOKEN", AUTH_TOKEN),
        ("CLOUD_TRIAL_ID", TRIAL_ID),
        ("CLOUD_DOCUMENT_ID", DOCUMENT_ID),
    ]
    if not val
]

pytestmark = [
    pytest.mark.cloud,
    pytest.mark.skipif(
        bool(_missing),
        reason=f"Cloud tests skipped — missing env vars: {', '.join(_missing)}",
    ),
]


@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        timeout=30.0,
    ) as c:
        yield c


@pytest.fixture(scope="module")
def created_ids() -> List[str]:
    """Collects session IDs created during tests so we can clean up after."""
    return []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client: httpx.Client, created_ids: List[str]):
    yield
    for sid in created_ids:
        try:
            client.delete(f"/api/chat-sessions/{sid}")
        except Exception:
            pass


class TestCreateChatSessionCloud:
    """POST /api/chat-sessions/ against live Cloud Run."""

    def test_bare_title_only(self, client: httpx.Client, created_ids: List[str]):
        """Minimal payload — all link fields should come back as null."""
        r = client.post(
            "/api/chat-sessions/",
            json={"title": "cloud-test-bare"},
        )
        assert r.status_code == 201, r.text
        data = r.json()

        assert data["title"] == "cloud-test-bare"
        assert data["trial_id"] is None
        assert data["document_id"] is None
        assert data["document_name"] is None
        assert uuid.UUID(data["id"])  # valid UUID
        assert data["created_at"] is not None

        created_ids.append(data["id"])

    def test_full_payload_echoes_link_fields(
        self, client: httpx.Client, created_ids: List[str]
    ):
        """Full payload — trial_id, document_id, document_name must round-trip."""
        payload = {
            "title": "cloud-test-full",
            "trial_id": TRIAL_ID,
            "document_id": DOCUMENT_ID,
            "document_name": "Protocol v2.pdf",
        }
        r = client.post("/api/chat-sessions/", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()

        assert data["title"] == "cloud-test-full"
        assert data["trial_id"] == TRIAL_ID
        assert data["document_id"] == DOCUMENT_ID
        assert data["document_name"] == "Protocol v2.pdf"

        created_ids.append(data["id"])

    def test_spoofed_user_id_is_ignored(
        self, client: httpx.Client, created_ids: List[str]
    ):
        """
        Sending user_id in the body must NOT set the DB's user_id column.
        Pydantic silently drops unknown fields; the route always uses
        member.profile_id from the JWT. Endpoint still returns 201.
        """
        spoofed = "00000000-0000-0000-0000-000000000000"
        r = client.post(
            "/api/chat-sessions/",
            json={"title": "cloud-test-spoof", "user_id": spoofed},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["title"] == "cloud-test-spoof"
        created_ids.append(data["id"])

        # The spoofed id shouldn't have leaked into the list response either —
        # the GET list filters by `user_id == member.profile_id`, so the new
        # row must appear there. If the spoof had stuck, it wouldn't.
        list_r = client.get("/api/chat-sessions/")
        assert list_r.status_code == 200
        ids = [s["id"] for s in list_r.json()]
        assert data["id"] in ids, (
            "Session missing from caller's list — user_id may have been "
            "set from the spoofed body value instead of member.profile_id."
        )

    def test_nonexistent_document_id_rejected_by_fk(self, client: httpx.Client):
        """
        document_id is a FK to documents(id); a random UUID should fail.
        FastAPI's default behavior on uncaught exceptions is a 500.
        """
        r = client.post(
            "/api/chat-sessions/",
            json={
                "title": "cloud-test-bad-fk",
                "document_id": str(uuid.uuid4()),
            },
        )
        assert r.status_code >= 400, (
            f"Expected failure for non-existent document_id, got {r.status_code}: {r.text}"
        )


class TestListChatSessionsCloud:
    """GET /api/chat-sessions/ surfaces the new fields."""

    def test_list_returns_new_fields(self, client: httpx.Client):
        r = client.get("/api/chat-sessions/")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

        if not data:
            pytest.skip("No chat sessions visible for this user — nothing to assert on shape")

        session = data[0]
        for key in ("id", "title", "trial_id", "document_id", "document_name",
                    "created_at", "updated_at"):
            assert key in session, f"Missing `{key}` in GET / response"

    def test_list_filtered_by_trial(self, client: httpx.Client):
        r = client.get(f"/api/chat-sessions/?trial_id={TRIAL_ID}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        for s in data:
            assert s["trial_id"] == TRIAL_ID
