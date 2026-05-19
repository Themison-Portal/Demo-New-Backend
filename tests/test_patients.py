"""
Tests for patient endpoints — /api/patients.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from tests.conftest import (
    NOW,
    TEST_MEMBER_ID,
    TEST_ORG_ID,
    make_scalars_result,
)

PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_ORG_ID = UUID("99999999-9999-9999-9999-999999999999")


def _make_mock_patient(**overrides):
    """Create a mock patient with all PatientResponse fields."""
    p = MagicMock()
    defaults = dict(
        id=PATIENT_ID,
        patient_code="PAT-12345",
        first_name="John",
        last_name="Doe",
        organization_id=TEST_ORG_ID,
        is_active=True,
        date_of_birth=None,
        gender=None,
        phone_number=None,
        email=None,
        street_address=None,
        city=None,
        state_province=None,
        postal_code=None,
        country="United States",
        emergency_contact_name=None,
        emergency_contact_phone=None,
        emergency_contact_relationship=None,
        height_cm=None,
        weight_kg=None,
        blood_type=None,
        medical_history=None,
        current_medications=None,
        known_allergies=None,
        primary_physician_name=None,
        primary_physician_phone=None,
        insurance_provider=None,
        insurance_policy_number=None,
        consent_signed=False,
        consent_date=None,
        screening_notes=None,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    for attr, value in defaults.items():
        setattr(p, attr, value)
    return p


# ---------------------------------------------------------------------------
# Generate code
# ---------------------------------------------------------------------------
class TestGeneratePatientCode:

    def test_generate_patient_code(self, authed_client, mock_db):
        """GET /api/patients/generate-code returns a PAT-XXXXX code."""
        # scalar_one() returns 0 => code is unique on first try
        result = MagicMock()
        result.scalar_one.return_value = 0
        mock_db.execute.return_value = result

        response = authed_client.get("/api/patients/generate-code")

        assert response.status_code == 200
        data = response.json()
        assert "patient_code" in data
        assert data["patient_code"].startswith("PAT-")
        assert len(data["patient_code"]) == 9  # PAT- + 5 digits


# ---------------------------------------------------------------------------
# List patients
# ---------------------------------------------------------------------------
class TestListPatients:

    def test_list_patients(self, authed_client, mock_db):
        """GET /api/patients/ returns a list of patients."""
        patient = _make_mock_patient()
        mock_db.execute.return_value = make_scalars_result(all_items=[patient])

        response = authed_client.get("/api/patients/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["patient_code"] == "PAT-12345"


# ---------------------------------------------------------------------------
# Get patient
# ---------------------------------------------------------------------------
class TestGetPatient:

    def test_get_patient_success(self, authed_client, mock_db):
        """GET /api/patients/{id} returns the patient when found."""
        patient = _make_mock_patient()
        mock_db.execute.return_value = make_scalars_result(first=patient)

        response = authed_client.get(f"/api/patients/{PATIENT_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(PATIENT_ID)
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"

    def test_get_patient_not_found(self, authed_client, mock_db):
        """GET /api/patients/{id} returns 404 when not found."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.get(f"/api/patients/{PATIENT_ID}")

        assert response.status_code == 404

    def test_get_patient_wrong_org(self, authed_client, mock_db):
        """GET /api/patients/{id} returns 404 when patient belongs to another org."""
        patient = _make_mock_patient(organization_id=OTHER_ORG_ID)
        mock_db.execute.return_value = make_scalars_result(first=patient)

        response = authed_client.get(f"/api/patients/{PATIENT_ID}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Create patient
# ---------------------------------------------------------------------------
class TestCreatePatient:

    def test_create_patient(self, authed_client, mock_db):
        """POST /api/patients/ with valid data returns 201."""
        patient = _make_mock_patient(patient_code="PAT-99999")

        async def fake_refresh(obj):
            obj.id = PATIENT_ID
            obj.patient_code = "PAT-99999"
            obj.first_name = None
            obj.last_name = None
            obj.organization_id = TEST_ORG_ID
            obj.is_active = True
            obj.date_of_birth = None
            obj.gender = None
            obj.phone_number = None
            obj.email = None
            obj.street_address = None
            obj.city = None
            obj.state_province = None
            obj.postal_code = None
            obj.country = "United States"
            obj.emergency_contact_name = None
            obj.emergency_contact_phone = None
            obj.emergency_contact_relationship = None
            obj.height_cm = None
            obj.weight_kg = None
            obj.blood_type = None
            obj.medical_history = None
            obj.current_medications = None
            obj.known_allergies = None
            obj.primary_physician_name = None
            obj.primary_physician_phone = None
            obj.insurance_provider = None
            obj.insurance_policy_number = None
            obj.consent_signed = False
            obj.consent_date = None
            obj.screening_notes = None
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        response = authed_client.post(
            "/api/patients/",
            json={"patient_code": "PAT-99999"},
        )

        assert response.status_code == 201

    def test_create_patient_missing_code(self, authed_client, mock_db):
        """POST /api/patients/ without patient_code returns 422."""
        response = authed_client.post("/api/patients/", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Update patient
# ---------------------------------------------------------------------------
class TestUpdatePatient:

    def test_update_patient_success(self, authed_client, mock_db):
        """PUT /api/patients/{id} updates and returns 200."""
        patient = _make_mock_patient()

        # First call: crud.get inside the route (org check)
        # Second call: crud.get inside crud.update
        # Then commit + refresh
        mock_db.execute.side_effect = [
            make_scalars_result(first=patient),  # route-level get
            make_scalars_result(first=patient),  # crud.update's internal get
        ]

        async def fake_refresh(obj):
            obj.first_name = "Jane"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        response = authed_client.put(
            f"/api/patients/{PATIENT_ID}",
            json={"first_name": "Jane"},
        )

        assert response.status_code == 200

    def test_update_patient_not_found(self, authed_client, mock_db):
        """PUT /api/patients/{id} returns 404 when patient not found."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.put(
            f"/api/patients/{PATIENT_ID}",
            json={"first_name": "Jane"},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete patient
# ---------------------------------------------------------------------------
class TestDeletePatient:

    def test_delete_patient_success(self, authed_client, mock_db):
        """DELETE /api/patients/{id} soft-deletes and returns 204."""
        patient = _make_mock_patient()

        # First call: crud.get in route (org check)
        # Second call: crud.get inside crud.update
        # Then commit + refresh
        mock_db.execute.side_effect = [
            make_scalars_result(first=patient),  # route-level get
            make_scalars_result(first=patient),  # crud.update's internal get
        ]
        mock_db.refresh = AsyncMock()

        response = authed_client.delete(f"/api/patients/{PATIENT_ID}")

        assert response.status_code == 204

    def test_delete_patient_not_found(self, authed_client, mock_db):
        """DELETE /api/patients/{id} returns 404 when patient not found."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.delete(f"/api/patients/{PATIENT_ID}")

        assert response.status_code == 404
