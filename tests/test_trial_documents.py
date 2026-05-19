"""
Tests for trial document endpoints — GET /, GET /{id}, POST /upload, PUT /{id}, DELETE /{id}
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, TEST_TRIAL_ID, NOW, make_scalars_result, make_rows_result

DOC_ID = UUID("aabbccdd-aabb-ccdd-eeff-aabbccddeeff")


@pytest.fixture
def mock_doc():
    doc = MagicMock()
    doc.id = DOC_ID
    doc.document_name = "protocol.pdf"
    doc.document_type = "protocol"
    doc.document_url = "trials/123/protocol.pdf"
    doc.trial_id = TEST_TRIAL_ID
    doc.uploaded_by = TEST_MEMBER_ID
    doc.status = "active"
    doc.file_size = 2048
    doc.mime_type = "application/pdf"
    doc.description = "Protocol doc"
    doc.version = 1
    doc.amendment_number = None
    doc.is_latest = True
    doc.tags = None
    doc.warning = None
    doc.created_at = NOW
    doc.updated_at = NOW
    return doc


class TestListTrialDocuments:

    def test_list_trial_documents(self, authed_client, mock_db, mock_doc):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_doc])
        )
        resp = authed_client.get("/api/trial-documents/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_with_trial_filter(self, authed_client, mock_db, mock_doc):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_doc])
        )
        resp = authed_client.get(f"/api/trial-documents/?trial_id={TEST_TRIAL_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestGetTrialDocument:

    def test_get_document_success(self, authed_client, mock_db, mock_doc):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_doc)
        )
        resp = authed_client.get(f"/api/trial-documents/{DOC_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_name"] == "protocol.pdf"

    def test_get_document_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.get(f"/api/trial-documents/{DOC_ID}")
        assert resp.status_code == 404


class TestUploadTrialDocument:

    def test_upload_document(self, storage_client, mock_db, mock_storage, mock_trial):
        # 1st execute: CRUDBase(Trial).get(trial_id) -> trial exists
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_trial)
        )

        async def fake_refresh(obj):
            obj.id = DOC_ID
            obj.document_name = "protocol.pdf"
            obj.document_type = "protocol"
            obj.document_url = "uploads/test/file.pdf"
            obj.trial_id = TEST_TRIAL_ID
            obj.uploaded_by = TEST_MEMBER_ID
            obj.status = "active"
            obj.file_size = 1024
            obj.mime_type = "application/pdf"
            obj.description = ""
            obj.version = None
            obj.amendment_number = None
            obj.is_latest = None
            obj.tags = None
            obj.warning = None
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = storage_client.post(
            "/api/trial-documents/upload",
            files={"file": ("protocol.pdf", BytesIO(b"fake pdf content"), "application/pdf")},
            data={
                "trial_id": str(TEST_TRIAL_ID),
                "document_name": "protocol.pdf",
                "document_type": "protocol",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_name"] == "protocol.pdf"
        assert data["status"] == "active"
        mock_storage.upload_file.assert_called_once()

    def test_upload_document_trial_not_found(self, storage_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = storage_client.post(
            "/api/trial-documents/upload",
            files={"file": ("protocol.pdf", BytesIO(b"fake pdf content"), "application/pdf")},
            data={
                "trial_id": str(TEST_TRIAL_ID),
                "document_name": "protocol.pdf",
                "document_type": "protocol",
            },
        )
        assert resp.status_code == 404


class TestUpdateTrialDocument:

    def test_update_document(self, authed_client, mock_db, mock_doc):
        # 1st execute: crud.get in endpoint, 2nd execute: crud.get inside crud.update
        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_doc),
            make_scalars_result(first=mock_doc),
        ])

        async def fake_refresh(obj):
            obj.document_name = "Updated Protocol"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.put(f"/api/trial-documents/{DOC_ID}", json={
            "document_name": "Updated Protocol",
        })
        assert resp.status_code == 200

    def test_update_document_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.put(f"/api/trial-documents/{DOC_ID}", json={
            "document_name": "Updated Protocol",
        })
        assert resp.status_code == 404


class TestDeleteTrialDocument:

    def test_delete_document(self, storage_client, mock_db, mock_doc, mock_storage):
        # 1st execute: crud.get in endpoint, 2nd execute: crud.get inside crud.delete
        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_doc),
            make_scalars_result(first=mock_doc),
        ])
        resp = storage_client.delete(f"/api/trial-documents/{DOC_ID}")
        assert resp.status_code == 204
        mock_storage.delete_file.assert_called_once()

    def test_delete_document_not_found(self, storage_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = storage_client.delete(f"/api/trial-documents/{DOC_ID}")
        assert resp.status_code == 404
