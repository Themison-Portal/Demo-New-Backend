"""
Unit tests for member endpoints — /api/members
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi.testclient import TestClient

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, NOW, make_scalars_result, make_rows_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TARGET_MEMBER_ID = UUID("11111111-1111-1111-1111-111111111111")
TARGET_PROFILE_ID = UUID("22222222-2222-2222-2222-222222222222")
WRONG_ORG_ID = UUID("99999999-9999-9999-9999-999999999999")


@pytest.fixture
def mock_profile():
    """Mock Profile returned by the /me endpoint."""
    p = MagicMock()
    p.id = TEST_PROFILE_ID
    p.first_name = "Test"
    p.last_name = "Admin"
    p.email = "admin@test.com"
    return p


@pytest.fixture
def mock_target_member():
    """Mock member that is the target of update/delete operations."""
    m = MagicMock()
    m.id = TARGET_MEMBER_ID
    m.name = "Target"
    m.email = "target@test.com"
    m.organization_id = TEST_ORG_ID
    m.profile_id = TARGET_PROFILE_ID
    m.default_role = "staff"
    m.onboarding_completed = False
    m.invited_by = TEST_MEMBER_ID
    m.created_at = NOW
    m.updated_at = NOW
    m.first_name = None
    m.last_name = None
    return m


# =========================================================================
# GET /api/members/me
# =========================================================================
class TestGetMe:
    """Tests for GET /api/members/me."""

    def test_get_me(self, authed_client: TestClient, mock_db, mock_profile):
        """GET /me returns current member info with profile fields."""
        mock_db.execute.return_value = make_scalars_result(first=mock_profile)

        response = authed_client.get("/api/members/me")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Admin"
        assert data["email"] == "admin@test.com"
        assert data["first_name"] == "Test"
        assert data["last_name"] == "Admin"


# =========================================================================
# GET /api/members/me/trial-assignments
# =========================================================================
class TestGetTrialAssignments:
    """Tests for GET /api/members/me/trial-assignments."""

    def test_get_trial_assignments_empty(self, authed_client: TestClient, mock_db):
        """GET /me/trial-assignments returns empty list when no assignments."""
        mock_db.execute.return_value = make_rows_result([])

        response = authed_client.get("/api/members/me/trial-assignments")

        assert response.status_code == 200
        assert response.json() == []


# =========================================================================
# GET /api/members/
# =========================================================================
class TestListMembers:
    """Tests for GET /api/members/."""

    def test_list_members(self, authed_client: TestClient, mock_db, mock_member):
        """GET / returns list of members in the organization."""
        mock_db.execute.return_value = make_scalars_result(all_items=[mock_member])

        response = authed_client.get("/api/members/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


# =========================================================================
# PUT /api/members/{member_id}
# =========================================================================
class TestUpdateMember:
    """Tests for PUT /api/members/{member_id}."""

    def test_update_member_success(
        self, authed_client: TestClient, mock_db, mock_target_member
    ):
        """PUT /{id} updates and returns the member."""
        updated = MagicMock()
        updated.id = mock_target_member.id
        updated.name = "New Name"
        updated.email = mock_target_member.email
        updated.organization_id = TEST_ORG_ID
        updated.profile_id = TARGET_PROFILE_ID
        updated.default_role = "staff"
        updated.onboarding_completed = False
        updated.invited_by = TEST_MEMBER_ID
        updated.created_at = NOW
        updated.updated_at = NOW

        # Call 1: endpoint's crud.get (org check)
        # Call 2: CRUDBase.update's internal get
        # Then commit + refresh (already mocked on mock_db)
        mock_db.execute.side_effect = [
            make_scalars_result(first=mock_target_member),
            make_scalars_result(first=mock_target_member),
        ]

        response = authed_client.put(
            f"/api/members/{TARGET_MEMBER_ID}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200

    def test_update_member_not_found(self, authed_client: TestClient, mock_db):
        """PUT /{id} returns 404 when member does not exist."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.put(
            f"/api/members/{TARGET_MEMBER_ID}",
            json={"name": "New Name"},
        )

        assert response.status_code == 404

    def test_update_member_wrong_org(
        self, authed_client: TestClient, mock_db, mock_target_member
    ):
        """PUT /{id} returns 404 when target belongs to a different org."""
        mock_target_member.organization_id = WRONG_ORG_ID
        mock_db.execute.return_value = make_scalars_result(first=mock_target_member)

        response = authed_client.put(
            f"/api/members/{TARGET_MEMBER_ID}",
            json={"name": "New Name"},
        )

        assert response.status_code == 404


# =========================================================================
# DELETE /api/members/{member_id}
# =========================================================================
class TestDeleteMember:
    """Tests for DELETE /api/members/{member_id}."""

    def test_delete_member_success(
        self, authed_client: TestClient, mock_db, mock_target_member
    ):
        """DELETE /{id} removes the member and returns 204."""
        # Call 1: endpoint's crud.get (org check)
        # Call 2: CRUDBase.delete's internal get
        # Then db.delete + db.commit (already mocked)
        mock_db.execute.side_effect = [
            make_scalars_result(first=mock_target_member),
            make_scalars_result(first=mock_target_member),
        ]

        response = authed_client.delete(f"/api/members/{TARGET_MEMBER_ID}")

        assert response.status_code == 204

    def test_delete_member_not_found(self, authed_client: TestClient, mock_db):
        """DELETE /{id} returns 404 when member does not exist."""
        mock_db.execute.return_value = make_scalars_result(first=None)

        response = authed_client.delete(f"/api/members/{TARGET_MEMBER_ID}")

        assert response.status_code == 404
