"""
Tests for chat message endpoints — GET /, POST /, PUT /{id}, DELETE /{id}
"""

import pytest
from typing import Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi.testclient import TestClient

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, NOW, make_scalars_result

from app.main import app
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db

TEST_SESSION_ID = UUID("77777777-7777-7777-7777-777777777777")
TEST_MESSAGE_ID = UUID("88888888-8888-8888-8888-888888888888")


@pytest.fixture
def mock_message():
    m = MagicMock()
    m.id = TEST_MESSAGE_ID
    m.session_id = TEST_SESSION_ID
    m.content = "Hello"
    m.role = "user"
    m.user_id = TEST_MEMBER_ID
    m.created_at = NOW
    m.updated_at = NOW
    m.deleted_at = None
    return m


@pytest.fixture
def mock_chat_session():
    s = MagicMock()
    s.id = TEST_SESSION_ID
    s.updated_at = NOW
    return s


@pytest.fixture
def staff_msg_client(mock_staff_member, mock_db):
    """Staff client with a message whose user_id differs from staff member id."""
    mock_msg = MagicMock()
    mock_msg.id = TEST_MESSAGE_ID
    mock_msg.user_id = TEST_MEMBER_ID  # not the staff member
    mock_msg.content = "Hello"
    mock_msg.role = "user"
    mock_msg.session_id = TEST_SESSION_ID
    mock_msg.created_at = NOW
    mock_msg.updated_at = NOW
    mock_msg.deleted_at = None

    mock_db.execute = AsyncMock(return_value=make_scalars_result(first=mock_msg))

    app.dependency_overrides[get_current_member] = lambda: mock_staff_member
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestListMessages:

    def test_list_messages(self, authed_client, mock_db, mock_message):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_message])
        )
        resp = authed_client.get(f"/api/chat-messages/?session_id={TEST_SESSION_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == str(TEST_MESSAGE_ID)
        assert data[0]["session_id"] == str(TEST_SESSION_ID)
        assert data[0]["content"] == "Hello"
        assert data[0]["role"] == "user"
        assert data[0]["created_at"] == NOW.isoformat()

    def test_list_messages_empty(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[])
        )
        resp = authed_client.get(f"/api/chat-messages/?session_id={TEST_SESSION_ID}")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateMessage:

    def test_create_message(self, authed_client, mock_db, mock_chat_session):
        # First execute: find session
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_chat_session)
        )

        async def fake_refresh(obj):
            obj.id = TEST_MESSAGE_ID
            obj.session_id = TEST_SESSION_ID
            obj.content = obj.content  # keep what was set
            obj.role = "user"
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.post(
            "/api/chat-messages/",
            json={
                "session_id": str(TEST_SESSION_ID),
                "content": "Hello",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == str(TEST_MESSAGE_ID)
        assert data["session_id"] == str(TEST_SESSION_ID)
        assert data["content"] == "Hello"
        assert data["role"] == "user"
        assert data["created_at"] == NOW.isoformat()

    def test_create_message_session_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.post(
            "/api/chat-messages/",
            json={
                "session_id": str(TEST_SESSION_ID),
                "content": "Hello",
            },
        )
        assert resp.status_code == 404


class TestUpdateMessage:

    def test_update_message_author(self, authed_client, mock_db, mock_message):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_message)
        )

        async def fake_refresh(obj):
            obj.id = TEST_MESSAGE_ID
            obj.session_id = TEST_SESSION_ID
            obj.content = obj.content
            obj.role = "user"
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.put(
            f"/api/chat-messages/{TEST_MESSAGE_ID}?content=Updated"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(TEST_MESSAGE_ID)

    def test_update_message_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.put(
            f"/api/chat-messages/{TEST_MESSAGE_ID}?content=Updated"
        )
        assert resp.status_code == 404

    def test_update_message_not_author_not_admin(self, staff_msg_client):
        resp = staff_msg_client.put(
            f"/api/chat-messages/{TEST_MESSAGE_ID}?content=Updated"
        )
        assert resp.status_code == 403


class TestDeleteMessage:

    def test_delete_message_author(self, authed_client, mock_db, mock_message):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_message)
        )
        resp = authed_client.delete(f"/api/chat-messages/{TEST_MESSAGE_ID}")
        assert resp.status_code == 204

    def test_delete_message_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.delete(f"/api/chat-messages/{TEST_MESSAGE_ID}")
        assert resp.status_code == 404

    def test_delete_message_not_author_staff(self, staff_msg_client):
        resp = staff_msg_client.delete(f"/api/chat-messages/{TEST_MESSAGE_ID}")
        assert resp.status_code == 403
