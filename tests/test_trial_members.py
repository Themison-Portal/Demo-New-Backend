"""
Tests for trial member endpoints — GET /team/{trial_id}, GET /pending/{trial_id},
POST /, POST /pending
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_TRIAL_ID, NOW, make_scalars_result, make_rows_result

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.dependencies.trial_access import get_trial_with_access


ROLE_ID = UUID("22222222-2222-2222-2222-222222222222")
INVITATION_ID = UUID("33333333-3333-3333-3333-333333333333")
TRIAL_MEMBER_ID = UUID("44444444-4444-4444-4444-444444444444")
PENDING_MEMBER_ID = UUID("55555555-5555-5555-5555-555555555555")


class TestGetTrialTeam:

    def test_get_trial_team_empty(self, trial_client, mock_db):
        mock_db.execute = AsyncMock(return_value=make_rows_result([]))
        resp = trial_client.get(f"/api/trial-members/team/{TEST_TRIAL_ID}")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetPendingMembers:

    def test_get_pending_members_empty(self, trial_client, mock_db):
        mock_db.execute = AsyncMock(return_value=make_rows_result([]))
        resp = trial_client.get(f"/api/trial-members/pending/{TEST_TRIAL_ID}")
        assert resp.status_code == 200
        assert resp.json() == []


class TestAddTrialMember:

    def test_add_trial_member_admin(self, trial_client, mock_db):
        # mock refresh to set fields on the TrialMember object
        async def fake_refresh(obj):
            obj.id = TRIAL_MEMBER_ID
            obj.trial_id = TEST_TRIAL_ID
            obj.member_id = TEST_MEMBER_ID
            obj.role_id = ROLE_ID
            obj.start_date = None
            obj.end_date = None
            obj.is_active = True
            obj.created_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        # After create, two execute calls: fetch Member, fetch Role
        mock_member_obj = MagicMock()
        mock_member_obj.name = "Test Admin"
        mock_member_obj.email = "admin@test.com"

        mock_role_obj = MagicMock()
        mock_role_obj.name = "Investigator"
        mock_role_obj.permission_level = "read"

        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_member_obj),
            make_scalars_result(first=mock_role_obj),
        ])

        resp = trial_client.post("/api/trial-members/", json={
            "trial_id": str(TEST_TRIAL_ID),
            "member_id": str(TEST_MEMBER_ID),
            "role_id": str(ROLE_ID),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["member_name"] == "Test Admin"
        assert data["role_name"] == "Investigator"

    @pytest.fixture
    def staff_trial_client(self, mock_staff_member, mock_db, mock_trial):
        app.dependency_overrides[get_current_member] = lambda: mock_staff_member
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_trial_with_access] = lambda: mock_trial
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.clear()

    def test_add_trial_member_staff_forbidden(self, staff_trial_client):
        resp = staff_trial_client.post("/api/trial-members/", json={
            "trial_id": str(TEST_TRIAL_ID),
            "member_id": str(TEST_MEMBER_ID),
            "role_id": str(ROLE_ID),
        })
        assert resp.status_code == 403


class TestAddPendingMember:

    def test_add_pending_member(self, trial_client, mock_db):
        # mock refresh to set fields on the TrialMemberPending object
        async def fake_refresh(obj):
            obj.id = PENDING_MEMBER_ID
            obj.trial_id = TEST_TRIAL_ID
            obj.invitation_id = INVITATION_ID
            obj.role_id = ROLE_ID
            obj.invited_by = TEST_MEMBER_ID
            obj.created_at = NOW
            obj.notes = None

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        # After create, two execute calls: fetch Invitation, fetch Role
        mock_invitation = MagicMock()
        mock_invitation.email = "pending@test.com"
        mock_invitation.name = "Pending User"
        mock_invitation.status = "pending"

        mock_role_obj = MagicMock()
        mock_role_obj.name = "Coordinator"
        mock_role_obj.permission_level = "write"

        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_invitation),
            make_scalars_result(first=mock_role_obj),
        ])

        resp = trial_client.post("/api/trial-members/pending", json={
            "trial_id": str(TEST_TRIAL_ID),
            "invitation_id": str(INVITATION_ID),
            "role_id": str(ROLE_ID),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["invitation_email"] == "pending@test.com"
        assert data["role_name"] == "Coordinator"
