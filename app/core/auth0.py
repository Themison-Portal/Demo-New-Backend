"""
Auth0 JWKS client for RS256 JWT verification.

Fetches public keys from Auth0's JWKS endpoint, caches them in memory
with a 6-hour TTL, and refreshes on verification failure to handle key rotation.
"""

import logging
import time
from typing import Any, Dict, Optional

import httpx
from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: float = 0.0
_JWKS_CACHE_TTL = 6 * 60 * 60  # 6 hours


async def _fetch_jwks(domain: str) -> Dict[str, Any]:
    """Fetch JWKS from Auth0."""
    url = f"https://{domain}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()


async def _get_jwks(domain: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Return cached JWKS, refreshing if stale or forced."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if not force_refresh and _jwks_cache and (now - _jwks_cache_time) < _JWKS_CACHE_TTL:
        return _jwks_cache

    logger.info("Refreshing Auth0 JWKS from %s", domain)
    _jwks_cache = await _fetch_jwks(domain)
    _jwks_cache_time = now
    return _jwks_cache


def _find_rsa_key(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, str]]:
    """Find the RSA key matching the given kid in the JWKS."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return None


async def verify_auth0_token(token: str) -> Dict[str, Any]:
    """
    Verify an Auth0 RS256 JWT and return the decoded payload.

    Validates issuer, audience, and expiration claims.
    On key-not-found, refreshes JWKS once to handle rotation.

    Returns:
        Decoded JWT payload dict with ``sub``, ``email``, etc.

    Raises:
        ValueError: If token is invalid or verification fails.
    """
    settings = get_settings()
    domain = settings.auth0_domain
    audience = settings.auth0_audience

    if not domain or not audience:
        raise ValueError("Auth0 domain and audience must be configured")

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise ValueError(f"Invalid token header: {e}")

    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("Token header missing 'kid'")

    # Try with cached keys first
    jwks = await _get_jwks(domain)
    rsa_key = _find_rsa_key(jwks, kid)

    if not rsa_key:
        # Key rotation — refresh and retry once
        logger.info("Key kid=%s not found in cache, refreshing JWKS", kid)
        jwks = await _get_jwks(domain, force_refresh=True)
        rsa_key = _find_rsa_key(jwks, kid)

    if not rsa_key:
        raise ValueError(f"Unable to find matching key for kid={kid}")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"https://{domain}/",
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Token verification failed: {e}")
