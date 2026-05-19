"""
Auth0 Management API Client - Handles administrative tasks like creating users.
"""
import logging
import time
import httpx
from typing import Any, Dict, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)

class Auth0ManagementClient:
    def __init__(self):
        try:
            self.settings = get_settings()
            self.domain = self.settings.auth0_domain
            self.client_id = self.settings.auth0_client_id
            self.client_secret = self.settings.auth0_client_secret
            self.audience = f"https://{self.domain}/api/v2/" if self.domain else ""
        except Exception as e:
            logger.warning(f"Auth0 Management Client partially initialized: {e}")
            self.domain = ""
            self.client_id = ""
            self.client_secret = ""
            self.audience = ""
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    async def _get_access_token(self) -> str:
        """Get an Access Token for the Management API using Client Credentials flow (Cached)."""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        url = f"https://{self.domain}/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "grant_type": "client_credentials"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
            return self._token

    async def create_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """
        Create a new user in Auth0.
        Returns the Auth0 user object.
        """
        token = await self._get_access_token()
        url = f"https://{self.domain}/api/v2/users"
        
        payload = {
            "connection": "Username-Password-Authentication",
            "email": email,
            "password": password,
            "name": name,
            "email_verified": True,
            "verify_email": False, # We already validated via invitation code
            "user_metadata": {
                "source": "invitation"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 409:
                # User already exists, fetch it
                logger.warning(f"User {email} already exists in Auth0, retrieving record.")
                return await self.get_user_by_email(email)
            resp.raise_for_status()
            return resp.json()

    async def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Fetch user by email from Auth0."""
        token = await self._get_access_token()
        url = f"https://{self.domain}/api/v2/users-by-email"
        params = {"email": email}
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            users = resp.json()
            if not users:
                raise ValueError(f"User {email} not found in Auth0")
            return users[0]

# Global instance
auth0_mgmt = Auth0ManagementClient()
