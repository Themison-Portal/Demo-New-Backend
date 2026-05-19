"""
Tests for chat session endpoints — GET /, POST /, PUT /{id}, DELETE /{id}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, NOW, make_scalars_result

TEST_SESSION_ID = UUID("77777777-7777-7777-7777-777777777777")
TEST_TRIAL_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


@pytest.fixture
def mock_session():
    s = MagicMock()
    s.id = TEST_SESSION_ID
    s.title = "Test Chat"
    s.trial_id = None
    s.user_id = TEST_PROFILE_ID
    s.created_at = NOW
    s.updated_at = NOW
    return s


class TestListSessions:

    def test_list_sessions(self, authed_client, mock_db, mock_session):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_session])
        )
        resp = authed_client.get("/api/chat-sessions/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == str(TEST_SESSION_ID)
        assert data[0]["title"] == "Test Chat"
        assert data[0]["trial_id"] is None
        assert data[0]["created_at"] == NOW.isoformat()
        assert data[0]["updated_at"] == NOW.isoformat()

    def test_list_sessions_with_trial_filter(self, authed_client, mock_db, mock_session):
        mock_session.trial_id = TEST_TRIAL_ID
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_session])
        )
        resp = authed_client.get(f"/api/chat-sessions/?trial_id={TEST_TRIAL_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["trial_id"] == str(TEST_TRIAL_ID)

    def test_list_sessions_empty(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[])
        )
        resp = authed_client.get("/api/chat-sessions/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateSession:

    def test_create_session(self, authed_client, mock_db):
        async def fake_refresh(obj):
            obj.id = TEST_SESSION_ID
            obj.title = obj.title  # keep what was set
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.post(
            "/api/chat-sessions/",
            json={"title": "New Chat", "user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == str(TEST_SESSION_ID)
        assert data["title"] == "New Chat"
        assert data["created_at"] == NOW.isoformat()


class TestUpdateSession:

    def test_update_session_success(self, authed_client, mock_db, mock_session):
        updated_session = MagicMock()
        updated_session.id = TEST_SESSION_ID
        updated_session.title = "Updated"
        updated_session.created_at = NOW
        updated_session.updated_at = NOW

        # First call: crud.get in the route, second call: crud.update -> crud.get internally
        mock_db.execute = AsyncMock(
            side_effect=[
                make_scalars_result(first=mock_session),
                make_scalars_result(first=mock_session),
            ]
        )

        async def fake_refresh(obj):
            obj.id = TEST_SESSION_ID
            obj.title = "Updated"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.put(
            f"/api/chat-sessions/{TEST_SESSION_ID}",
            json={"title": "Updated"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(TEST_SESSION_ID)
        assert data["title"] == "Updated"

    def test_update_session_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.put(
            f"/api/chat-sessions/{TEST_SESSION_ID}",
            json={"title": "Updated"},
        )
        assert resp.status_code == 404


class TestDeleteSession:

    def test_delete_session_success(self, authed_client, mock_db, mock_session):
        # First call: crud.get in the route, second call: crud.delete -> crud.get internally
        mock_db.execute = AsyncMock(
            side_effect=[
                make_scalars_result(first=mock_session),
                make_scalars_result(first=mock_session),
            ]
        )
        resp = authed_client.delete(f"/api/chat-sessions/{TEST_SESSION_ID}")
        assert resp.status_code == 204

    def test_delete_session_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.delete(f"/api/chat-sessions/{TEST_SESSION_ID}")
        assert resp.status_code == 404
