"""
Tests for trial patient endpoints — /api/trial-patients.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from tests.conftest import (
    TEST_MEMBER_ID,
    TEST_ORG_ID,
    TEST_TRIAL_ID,
    NOW,
    make_scalars_result,
    make_rows_result,
)

ENROLLMENT_ID = UUID("44444444-4444-4444-4444-444444444444")
PATIENT_ID = UUID("55555555-5555-5555-5555-555555555555")


def _make_mock_trial_patient():
    """Create a mock TrialPatient with all expected fields."""
    tp = MagicMock()
    tp.id = ENROLLMENT_ID
    tp.trial_id = TEST_TRIAL_ID
    tp.patient_id = PATIENT_ID
    tp.enrollment_date = None
    tp.status = "enrolled"
    tp.randomization_code = None
    tp.notes = None
    tp.assigned_by = TEST_MEMBER_ID
    tp.created_at = NOW
    tp.updated_at = NOW
    tp.cost_data = None
    tp.patient_data = None
    tp.patient_code = None
    tp.patient_first_name = None
    tp.patient_last_name = None
    return tp


def _make_mock_patient():
    """Create a mock Patient with basic fields."""
    p = MagicMock()
    p.id = PATIENT_ID
    p.patient_code = "PAT-12345"
    p.first_name = "John"
    p.last_name = "Doe"
    return p


# ---------------------------------------------------------------------------
# List trial patients
# ---------------------------------------------------------------------------
class TestListTrialPatients:

    def test_list_trial_patients(self, authed_client, mock_db):
        """GET /api/trial-patients/?trial_id=... returns enriched list."""
        mock_tp = _make_mock_trial_patient()
        mock_patient = _make_mock_patient()
        mock_db.execute.return_value = make_rows_result([(mock_tp, mock_patient)])

        response = authed_client.get(
            f"/api/trial-patients/?trial_id={TEST_TRIAL_ID}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_trial_patients_empty(self, authed_client, mock_db):
        """GET /api/trial-patients/?trial_id=... returns empty list."""
        mock_db.execute.return_value = make_rows_result([])

        response = authed_client.get(
            f"/api/trial-patients/?trial_id={TEST_TRIAL_ID}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []


# ---------------------------------------------------------------------------
# Enroll patient
# ---------------------------------------------------------------------------
class TestEnrollPatient:

    def test_enroll_patient(self, authed_client, mock_db):
        """POST /api/trial-patients/ with valid data returns 201."""
        mock_patient = _make_mock_patient()

        async def fake_refresh(obj):
            obj.id = ENROLLMENT_ID
            obj.trial_id = TEST_TRIAL_ID
            obj.patient_id = PATIENT_ID
            obj.enrollment_date = None
            obj.status = "enrolled"
            obj.randomization_code = None
            obj.notes = None
            obj.assigned_by = TEST_MEMBER_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.cost_data = None
            obj.patient_data = None

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)
        mock_db.execute.return_value = make_scalars_result(first=mock_patient)

        response = authed_client.post(
            "/api/trial-patients/",
            json={
                "trial_id": str(TEST_TRIAL_ID),
                "patient_id": str(PATIENT_ID),
            },
        )

        assert response.status_code == 201

    def test_enroll_patient_missing_fields(self, authed_client, mock_db):
        """POST /api/trial-patients/ with empty body returns 422."""
        response = authed_client.post("/api/trial-patients/", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Update enrollment
# ---------------------------------------------------------------------------
class TestUpdateEnrollment:

    def test_update_enrollment_success(self, authed_client, mock_db):
        """PUT /api/trial-patients/{id} updates and returns 200."""
        mock_tp = _make_mock_trial_patient()

        # First call: CRUDBase.get (route-level)
        # Second call: CRUDBase.get inside CRUDBase.update
        mock_db.execute.side_effect = [
            make_scalars_result(first=mock_tp),
            make_scalars_result(first=mock_tp),
        ]

        async def fake_refresh(obj):
            obj.status = "completed"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        response = authed_client.put(
            f"/api/trial-patients/{ENROLLMENT_ID}",
            json={"status": "completed"},
        )

        assert response.status_code == 200

    def test_update_enrollment_not_found(self, authed_client, mock_db):
        """PUT /api/trial-patients/{id} returns 404 when not found."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.put(
            f"/api/trial-patients/{ENROLLMENT_ID}",
            json={"status": "completed"},
        )

        assert response.status_code == 404
