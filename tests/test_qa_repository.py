"""
Tests for QA repository endpoints — GET /, POST /, PUT /{id}/verify, DELETE /{id}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, TEST_TRIAL_ID, NOW, make_scalars_result, make_rows_result

QA_ITEM_ID = UUID("99999999-9999-9999-9999-999999999999")


@pytest.fixture
def mock_qa_item():
    item = MagicMock()
    item.id = QA_ITEM_ID
    item.trial_id = TEST_TRIAL_ID
    item.question = "What is X?"
    item.answer = "X is Y"
    item.created_by = TEST_MEMBER_ID
    item.created_at = NOW
    item.updated_at = NOW
    item.tags = ["test"]
    item.is_verified = False
    item.source = "manual"
    item.sources = None
    return item


class TestListQAItems:

    def test_list_qa_items(self, authed_client, mock_db, mock_qa_item):
        mock_member_obj = MagicMock()
        mock_member_obj.name = "Test Admin"
        mock_member_obj.email = "admin@test.com"
        mock_member_obj.profile_id = TEST_PROFILE_ID
        mock_profile_obj = MagicMock(first_name="Test", last_name="Admin")
        mock_db.execute = AsyncMock(
            return_value=make_rows_result([(mock_qa_item, mock_member_obj, mock_profile_obj)])
        )
        resp = authed_client.get(f"/api/qa-repository/?trial_id={TEST_TRIAL_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["question"] == "What is X?"

    def test_list_qa_items_empty(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(return_value=make_rows_result([]))
        resp = authed_client.get(f"/api/qa-repository/?trial_id={TEST_TRIAL_ID}")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateQAItem:

    def test_create_qa_item(self, authed_client, mock_db):
        async def fake_refresh(obj):
            obj.id = QA_ITEM_ID
            obj.trial_id = TEST_TRIAL_ID
            obj.question = "Q?"
            obj.answer = "A"
            obj.created_by = TEST_MEMBER_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.tags = None
            obj.is_verified = False
            obj.source = None
            obj.sources = None

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.post("/api/qa-repository/", json={
            "question": "Q?",
            "answer": "A",
            "trial_id": str(TEST_TRIAL_ID),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["question"] == "Q?"
        assert data["answer"] == "A"
        assert data["creator_name"] == "Test Admin"
        assert data["creator_email"] == "admin@test.com"

    def test_create_qa_item_missing_fields(self, authed_client):
        resp = authed_client.post("/api/qa-repository/", json={})
        assert resp.status_code == 422


class TestVerifyQAItem:

    def test_verify_qa_item(self, authed_client, mock_db, mock_qa_item):
        # Add response model fields that QAItemResponse expects
        mock_qa_item.creator_name = None
        mock_qa_item.creator_email = None

        # 1st execute: crud.get in endpoint, 2nd execute: crud.get inside crud.update
        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_qa_item),
            make_scalars_result(first=mock_qa_item),
        ])

        async def fake_refresh(obj):
            obj.is_verified = True

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.put(f"/api/qa-repository/{QA_ITEM_ID}/verify")
        assert resp.status_code == 200

    def test_verify_qa_item_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.put(f"/api/qa-repository/{QA_ITEM_ID}/verify")
        assert resp.status_code == 404


class TestDeleteQAItem:

    def test_delete_qa_item(self, authed_client, mock_db, mock_qa_item):
        # 1st execute: crud.get in endpoint, 2nd execute: crud.get inside crud.delete
        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_qa_item),
            make_scalars_result(first=mock_qa_item),
        ])
        resp = authed_client.delete(f"/api/qa-repository/{QA_ITEM_ID}")
        assert resp.status_code == 204

    def test_delete_qa_item_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.delete(f"/api/qa-repository/{QA_ITEM_ID}")
        assert resp.status_code == 404
