"""
Tests for role endpoints — GET /, POST /, DELETE /{role_id}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from tests.conftest import TEST_MEMBER_ID, TEST_ORG_ID, TEST_PROFILE_ID, TEST_TRIAL_ID, NOW, make_scalars_result, make_rows_result


ROLE_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def mock_role():
    r = MagicMock()
    r.id = ROLE_ID
    r.name = "Investigator"
    r.organization_id = TEST_ORG_ID
    r.permission_level = "read"
    r.created_by = TEST_MEMBER_ID
    r.created_at = NOW
    r.updated_at = NOW
    r.description = None
    return r


class TestListRoles:

    def test_list_roles(self, authed_client, mock_db, mock_role):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_role])
        )
        resp = authed_client.get("/api/roles/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestCreateRole:

    def test_create_role(self, authed_client, mock_db):
        def fake_refresh(obj):
            obj.id = ROLE_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.organization_id = TEST_ORG_ID
            obj.created_by = TEST_MEMBER_ID
            obj.name = "Coordinator"
            obj.description = None
            obj.permission_level = "read"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.post("/api/roles/", json={"name": "Coordinator"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Coordinator"

    def test_create_role_missing_name(self, authed_client):
        resp = authed_client.post("/api/roles/", json={})
        assert resp.status_code == 422


class TestDeleteRole:

    def test_delete_role_success(self, authed_client, mock_db, mock_role):
        """
        Delete flow:
        1. crud.get(role_id) -> db.execute -> scalars().first() = mock_role
        2. db.execute count query -> scalar_one() = 0
        3. crud.delete -> crud.get(role_id) -> db.execute -> scalars().first() = mock_role
        """
        result_get = make_scalars_result(first=mock_role)
        result_count = MagicMock(scalar_one=MagicMock(return_value=0))
        result_get_again = make_scalars_result(first=mock_role)

        mock_db.execute = AsyncMock(
            side_effect=[result_get, result_count, result_get_again]
        )

        resp = authed_client.delete(f"/api/roles/{ROLE_ID}")
        assert resp.status_code == 204

    def test_delete_role_not_found(self, authed_client, mock_db):
        result_get = make_scalars_result(first=None)
        mock_db.execute = AsyncMock(return_value=result_get)

        resp = authed_client.delete(f"/api/roles/{ROLE_ID}")
        assert resp.status_code == 404

    def test_delete_role_in_use(self, authed_client, mock_db, mock_role):
        result_get = make_scalars_result(first=mock_role)
        result_count = MagicMock(scalar_one=MagicMock(return_value=3))

        mock_db.execute = AsyncMock(
            side_effect=[result_get, result_count]
        )

        resp = authed_client.delete(f"/api/roles/{ROLE_ID}")
        assert resp.status_code == 409
