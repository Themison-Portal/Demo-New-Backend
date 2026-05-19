"""
Tests for patient document endpoints — GET /, POST /, PUT /{id}, DELETE /{id}
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, TEST_TRIAL_ID, NOW, make_scalars_result, make_rows_result

DOC_ID = UUID("aabbccdd-aabb-ccdd-eeff-aabbccddeeff")
PATIENT_ID = UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture
def mock_doc():
    doc = MagicMock()
    doc.id = DOC_ID
    doc.document_name = "test.pdf"
    doc.document_type = "protocol"
    doc.document_url = "patients/123/test.pdf"
    doc.patient_id = PATIENT_ID
    doc.uploaded_by = TEST_MEMBER_ID
    doc.status = "active"
    doc.file_size = 1024
    doc.mime_type = "application/pdf"
    doc.description = ""
    doc.version = 1
    doc.is_latest = True
    doc.tags = None
    doc.created_at = NOW
    doc.updated_at = NOW
    return doc


class TestListPatientDocuments:

    def test_list_patient_documents(self, authed_client, mock_db, mock_doc):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_doc])
        )
        resp = authed_client.get("/api/patient-documents/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_with_patient_filter(self, authed_client, mock_db, mock_doc):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_doc])
        )
        resp = authed_client.get(f"/api/patient-documents/?patient_id={PATIENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestUploadPatientDocument:

    def test_upload_document(self, storage_client, mock_db, mock_storage):
        async def fake_refresh(obj):
            obj.id = DOC_ID
            obj.document_name = "Test Doc"
            obj.document_type = "protocol"
            obj.document_url = "uploads/test/file.pdf"
            obj.patient_id = PATIENT_ID
            obj.uploaded_by = TEST_MEMBER_ID
            obj.status = "active"
            obj.file_size = 1024
            obj.mime_type = "application/pdf"
            obj.description = ""
            obj.version = 1
            obj.is_latest = True
            obj.tags = None
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = storage_client.post(
            "/api/patient-documents/",
            files={"file": ("test.pdf", BytesIO(b"fake pdf content"), "application/pdf")},
            data={
                "patient_id": str(PATIENT_ID),
                "document_name": "Test Doc",
                "document_type": "protocol",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_name"] == "Test Doc"
        assert data["status"] == "active"
        mock_storage.upload_file.assert_called_once()


class TestUpdatePatientDocument:

    def test_update_document(self, authed_client, mock_db, mock_doc):
        # 1st execute: crud.get in endpoint, 2nd execute: crud.get inside crud.update
        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_doc),
            make_scalars_result(first=mock_doc),
        ])

        async def fake_refresh(obj):
            obj.document_name = "Updated"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.put(f"/api/patient-documents/{DOC_ID}", json={
            "document_name": "Updated",
        })
        assert resp.status_code == 200

    def test_update_document_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.put(f"/api/patient-documents/{DOC_ID}", json={
            "document_name": "Updated",
        })
        assert resp.status_code == 404


class TestDeletePatientDocument:

    def test_delete_document(self, storage_client, mock_db, mock_doc, mock_storage):
        # 1st execute: crud.get in endpoint, 2nd execute: crud.get inside crud.delete
        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_doc),
            make_scalars_result(first=mock_doc),
        ])
        resp = storage_client.delete(f"/api/patient-documents/{DOC_ID}")
        assert resp.status_code == 204
        mock_storage.delete_file.assert_called_once()

    def test_delete_document_not_found(self, storage_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = storage_client.delete(f"/api/patient-documents/{DOC_ID}")
        assert resp.status_code == 404
