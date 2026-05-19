"""
Tests for trial endpoints — GET /, GET /{id}, POST /with-assignments, PUT /{id},
GET /{id}/template, PUT /{id}/template
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


class TestListTrials:

    def test_list_trials(self, authed_client, mock_db, mock_trial):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(all_items=[mock_trial])
        )
        resp = authed_client.get("/api/trials/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestGetTrial:

    def test_get_trial_success(self, authed_client, mock_db, mock_trial):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_trial)
        )
        resp = authed_client.get(f"/api/trials/{TEST_TRIAL_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Trial"

    def test_get_trial_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.get(f"/api/trials/{TEST_TRIAL_ID}")
        assert resp.status_code == 404

    def test_get_trial_wrong_org(self, authed_client, mock_db, mock_trial):
        mock_trial.organization_id = UUID("11111111-1111-1111-1111-111111111111")
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=mock_trial)
        )
        resp = authed_client.get(f"/api/trials/{TEST_TRIAL_ID}")
        assert resp.status_code == 404


class TestCreateTrialWithAssignments:

    def test_create_trial_with_assignments(self, authed_client, mock_db):
        async def fake_refresh(obj):
            obj.id = TEST_TRIAL_ID
            obj.name = "New Trial"
            obj.phase = "Phase I"
            obj.location = "Here"
            obj.sponsor = "Sponsor"
            obj.organization_id = TEST_ORG_ID
            obj.created_by = TEST_MEMBER_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.status = "planning"
            obj.description = None
            obj.image_url = None
            obj.study_start = None
            obj.estimated_close_out = None
            obj.budget_data = None

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.post("/api/trials/with-assignments", json={
            "name": "New Trial",
            "phase": "Phase I",
            "location": "Here",
            "sponsor": "Sponsor",
            "members": [],
            "pending_members": [],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Trial"
        assert data["status"] == "planning"

    def test_create_trial_missing_fields(self, authed_client):
        resp = authed_client.post("/api/trials/with-assignments", json={})
        assert resp.status_code == 422


class TestUpdateTrial:

    def test_update_trial_success(self, authed_client, mock_db, mock_trial):
        # First execute: get in endpoint, second execute: get in crud.update
        updated_trial = MagicMock()
        updated_trial.id = TEST_TRIAL_ID
        updated_trial.name = "Updated"
        updated_trial.phase = "Phase I"
        updated_trial.location = "Test Location"
        updated_trial.sponsor = "Test Sponsor"
        updated_trial.description = "A test trial"
        updated_trial.status = "active"
        updated_trial.organization_id = TEST_ORG_ID
        updated_trial.created_by = TEST_MEMBER_ID
        updated_trial.created_at = NOW
        updated_trial.updated_at = NOW
        updated_trial.image_url = None
        updated_trial.study_start = None
        updated_trial.estimated_close_out = None
        updated_trial.budget_data = None

        mock_db.execute = AsyncMock(side_effect=[
            make_scalars_result(first=mock_trial),   # get in endpoint
            make_scalars_result(first=mock_trial),   # get in crud.update
        ])

        async def fake_refresh(obj):
            obj.name = "Updated"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        resp = authed_client.put(f"/api/trials/{TEST_TRIAL_ID}", json={
            "name": "Updated",
        })
        assert resp.status_code == 200

    def test_update_trial_not_found(self, authed_client, mock_db):
        mock_db.execute = AsyncMock(
            return_value=make_scalars_result(first=None)
        )
        resp = authed_client.put(f"/api/trials/{TEST_TRIAL_ID}", json={
            "name": "Updated",
        })
        assert resp.status_code == 404


class TestGetTemplate:

    def test_get_template(self, trial_client, mock_trial):
        resp = trial_client.get(f"/api/trials/{TEST_TRIAL_ID}/template")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"visits": [], "assignees": {}}


class TestUpdateTemplateAccess:

    @pytest.fixture
    def staff_trial_client(self, mock_staff_member, mock_db, mock_trial):
        app.dependency_overrides[get_current_member] = lambda: mock_staff_member
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_trial_with_access] = lambda: mock_trial
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.clear()

    def test_update_template_staff_forbidden(self, staff_trial_client):
        resp = staff_trial_client.put(
            f"/api/trials/{TEST_TRIAL_ID}/template",
            json={"visits": [], "assignees": {}},
        )
        assert resp.status_code == 403
