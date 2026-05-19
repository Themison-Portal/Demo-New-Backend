"""
Tests for patient visit endpoints — /api/patient-visits.
"""

from datetime import date
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

VISIT_ID = UUID("66666666-6666-6666-6666-666666666666")
PATIENT_ID = UUID("55555555-5555-5555-5555-555555555555")


def _make_mock_visit():
    """Create a mock PatientVisit with all expected fields."""
    v = MagicMock()
    v.id = VISIT_ID
    v.patient_id = PATIENT_ID
    v.trial_id = TEST_TRIAL_ID
    v.doctor_id = TEST_MEMBER_ID
    v.visit_date = date(2026, 3, 1)
    v.visit_time = None
    v.visit_type = "follow_up"
    v.status = "scheduled"
    v.duration_minutes = None
    v.visit_number = None
    v.notes = None
    v.next_visit_date = None
    v.location = None
    v.created_at = NOW
    v.updated_at = NOW
    v.created_by = TEST_MEMBER_ID
    v.cost_data = None
    return v


def _make_mock_doctor():
    """Create a mock Member (doctor) with basic fields."""
    d = MagicMock()
    d.name = "Dr. Test"
    return d


def _make_mock_enrollment():
    """Create a mock enrollment (just needs to exist)."""
    return MagicMock()


# ---------------------------------------------------------------------------
# List visits
# ---------------------------------------------------------------------------
class TestListVisits:

    def test_list_visits(self, authed_client, mock_db):
        """GET /api/patient-visits/ returns enriched list."""
        mock_visit = _make_mock_visit()
        mock_doctor = _make_mock_doctor()
        mock_db.execute.return_value = make_rows_result([(mock_visit, mock_doctor)])

        response = authed_client.get("/api/patient-visits/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_visits_with_filters(self, authed_client, mock_db):
        """GET /api/patient-visits/?patient_id=...&trial_id=... returns filtered list."""
        mock_visit = _make_mock_visit()
        mock_doctor = _make_mock_doctor()
        mock_db.execute.return_value = make_rows_result([(mock_visit, mock_doctor)])

        response = authed_client.get(
            f"/api/patient-visits/?patient_id={PATIENT_ID}&trial_id={TEST_TRIAL_ID}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_visits_empty(self, authed_client, mock_db):
        """GET /api/patient-visits/ returns empty list."""
        mock_db.execute.return_value = make_rows_result([])

        response = authed_client.get("/api/patient-visits/")

        assert response.status_code == 200
        data = response.json()
        assert data == []


# ---------------------------------------------------------------------------
# Create visit
# ---------------------------------------------------------------------------
class TestCreateVisit:

    def test_create_visit_success(self, authed_client, mock_db):
        """POST /api/patient-visits/ with valid data returns 201."""
        mock_enrollment = _make_mock_enrollment()
        mock_doctor = _make_mock_doctor()

        # First execute: enrollment check
        # Second execute: fetch doctor after create
        mock_db.execute.side_effect = [
            make_scalars_result(first=mock_enrollment),
            make_scalars_result(first=mock_doctor),
        ]

        async def fake_refresh(obj):
            obj.id = VISIT_ID
            obj.patient_id = PATIENT_ID
            obj.trial_id = TEST_TRIAL_ID
            obj.doctor_id = TEST_MEMBER_ID
            obj.visit_date = date(2026, 3, 1)
            obj.visit_time = None
            obj.visit_type = "follow_up"
            obj.status = "scheduled"
            obj.duration_minutes = None
            obj.visit_number = None
            obj.notes = None
            obj.next_visit_date = None
            obj.location = None
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.created_by = TEST_MEMBER_ID
            obj.cost_data = None

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        response = authed_client.post(
            "/api/patient-visits/",
            json={
                "patient_id": str(PATIENT_ID),
                "trial_id": str(TEST_TRIAL_ID),
                "doctor_id": str(TEST_MEMBER_ID),
                "visit_date": "2026-03-01",
            },
        )

        assert response.status_code == 201

    def test_create_visit_not_enrolled(self, authed_client, mock_db):
        """POST /api/patient-visits/ returns 400 when patient not enrolled."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.post(
            "/api/patient-visits/",
            json={
                "patient_id": str(PATIENT_ID),
                "trial_id": str(TEST_TRIAL_ID),
                "doctor_id": str(TEST_MEMBER_ID),
                "visit_date": "2026-03-01",
            },
        )

        assert response.status_code == 400

    def test_create_visit_missing_fields(self, authed_client, mock_db):
        """POST /api/patient-visits/ with empty body returns 422."""
        response = authed_client.post("/api/patient-visits/", json={})

        assert response.status_code == 422
