"""
Tests for organization endpoints — /api/organizations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, TEST_TRIAL_ID, NOW, make_scalars_result, make_rows_result


@pytest.fixture
def mock_org():
    o = MagicMock()
    o.id = TEST_ORG_ID
    o.name = "Test Org"
    o.onboarding_completed = True
    o.support_enabled = False
    o.created_by = TEST_MEMBER_ID
    o.created_at = NOW
    o.updated_at = NOW
    return o


class TestGetMyOrg:

    def test_get_my_org_success(self, authed_client, mock_db, mock_org):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_org)
        )
        resp = authed_client.get("/api/organizations/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Org"

    def test_get_my_org_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.get("/api/organizations/me")
        assert resp.status_code == 404


class TestUpdateMyOrg:

    def test_update_my_org(self, authed_client, mock_db, mock_org):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_org)
        )
        resp = authed_client.put(
            "/api/organizations/me",
            json={"name": "New Name"},
        )
        assert resp.status_code == 200


class TestGetMetrics:

    def test_get_metrics(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one=MagicMock(return_value=10)),   # members
            MagicMock(scalar_one=MagicMock(return_value=5)),    # trials
            MagicMock(scalar_one=MagicMock(return_value=2)),    # active_trials
            MagicMock(scalar_one=MagicMock(return_value=20)),   # patients
            MagicMock(scalar_one=MagicMock(return_value=15)),   # documents
        ])
        resp = authed_client.get("/api/organizations/me/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_members"] == 10
        assert data["total_trials"] == 5
        assert data["active_trials"] == 2
        assert data["total_patients"] == 20
        assert data["total_documents"] == 15


class TestGetOrgById:

    def test_get_org_by_id_admin(self, authed_client, mock_db, mock_org):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_org)
        )
        resp = authed_client.get(f"/api/organizations/{TEST_ORG_ID}")
        assert resp.status_code == 200

    def test_get_org_by_id_staff_forbidden(self, staff_client):
        resp = staff_client.get(f"/api/organizations/{TEST_ORG_ID}")
        assert resp.status_code == 403


class TestUpdateOrgById:

    def test_update_org_by_id_staff_forbidden(self, staff_client):
        resp = staff_client.put(
            f"/api/organizations/{TEST_ORG_ID}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 403


class TestListOrgs:

    def test_list_orgs_admin(self, authed_client, mock_db, mock_org):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_org])
        )
        resp = authed_client.get("/api/organizations/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_orgs_staff_forbidden(self, staff_client):
        resp = staff_client.get("/api/organizations/")
        assert resp.status_code == 403


class TestCreateOrg:

    def test_create_org_admin(self, authed_client, mock_db):
        def fake_refresh(obj):
            obj.id = TEST_ORG_ID
            obj.name = "New Org"
            obj.onboarding_completed = False
            obj.support_enabled = False
            obj.created_by = TEST_MEMBER_ID
            obj.created_at = NOW
            obj.updated_at = NOW

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.post(
            "/api/organizations/",
            json={"name": "New Org"},
        )
        assert resp.status_code == 201


class TestDeleteMember:

    def test_delete_member_admin(self, authed_client, mock_db):
        mock_member_to_delete = MagicMock()
        mock_member_to_delete.id = UUID("11111111-1111-1111-1111-111111111111")
        mock_member_to_delete.email = "user@test.com"
        mock_member_to_delete.first_name = "John"
        mock_member_to_delete.last_name = "Doe"
        mock_member_to_delete.org_role = "staff"
        mock_member_to_delete.organization_id = TEST_ORG_ID
        mock_member_to_delete.deleted_at = None

        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_member_to_delete)
        )

        member_id = mock_member_to_delete.id
        resp = authed_client.delete(f"/api/organizations/members/{member_id}")
        assert resp.status_code == 200

    def test_delete_member_staff_forbidden(self, staff_client):
        member_id = UUID("11111111-1111-1111-1111-111111111111")
        resp = staff_client.delete(f"/api/organizations/members/{member_id}")
        assert resp.status_code == 403
