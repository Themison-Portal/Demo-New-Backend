"""
Tests for GET /auth/me endpoint.
"""

from unittest.mock import MagicMock

import pytest

from tests.conftest import (
    NOW,
    TEST_MEMBER_ID,
    TEST_ORG_ID,
    TEST_PROFILE_ID,
    make_scalars_result,
)


class TestGetMe:
    """Tests for GET /auth/me."""

    def _make_mock_profile(self):
        p = MagicMock()
        p.id = TEST_PROFILE_ID
        p.first_name = "Test"
        p.last_name = "Admin"
        p.email = "admin@test.com"
        return p

    def _make_mock_org(self):
        o = MagicMock()
        o.id = TEST_ORG_ID
        o.name = "Test Org"
        o.onboarding_completed = True
        return o

    def test_get_me_success(self, authed_client, mock_db, mock_member):
        """Both profile and organization are found."""
        profile = self._make_mock_profile()
        org = self._make_mock_org()

        mock_db.execute.side_effect = [
            make_scalars_result(first=profile),
            make_scalars_result(first=org),
        ]

        response = authed_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(TEST_PROFILE_ID)
        assert data["email"] == mock_member.email
        # member block
        assert data["member"]["id"] == str(TEST_MEMBER_ID)
        assert data["member"]["organization_id"] == str(TEST_ORG_ID)
        assert data["member"]["default_role"] == "admin"
        # profile block
        assert data["profile"]["id"] == str(TEST_PROFILE_ID)
        assert data["profile"]["first_name"] == "Test"
        assert data["profile"]["last_name"] == "Admin"
        assert data["profile"]["email"] == "admin@test.com"
        # organization block
        assert data["organization"]["id"] == str(TEST_ORG_ID)
        assert data["organization"]["name"] == "Test Org"
        assert data["organization"]["onboarding_completed"] is True

    def test_get_me_no_profile(self, authed_client, mock_db, mock_member):
        """Profile query returns None; profile fields should be null."""
        org = self._make_mock_org()

        mock_db.execute.side_effect = [
            make_scalars_result(first=None),   # no profile
            make_scalars_result(first=org),
        ]

        response = authed_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["id"] is None
        assert data["profile"]["first_name"] is None
        assert data["profile"]["last_name"] is None
        assert data["profile"]["email"] is None
        # organization should still be present
        assert data["organization"]["id"] == str(TEST_ORG_ID)

    def test_get_me_no_organization(self, authed_client, mock_db, mock_member):
        """Organization query returns None; organization should be null."""
        profile = self._make_mock_profile()

        mock_db.execute.side_effect = [
            make_scalars_result(first=profile),
            make_scalars_result(first=None),   # no org
        ]

        response = authed_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        # profile still present
        assert data["profile"]["id"] == str(TEST_PROFILE_ID)
        # organization is None
        assert data["organization"] is None
