"""
Authentication dependencies — Auth0 JWT verification.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.auth0 import verify_auth0_token
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.profiles import Profile

logger = logging.getLogger(__name__)

# Make HTTPBearer optional when auth is disabled
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Verify Auth0 JWT and return basic user info.

    Returns dict with ``id`` (profile UUID), ``email``, ``auth0_sub``.

    If AUTH_DISABLED=true in .env, returns a mock test user.
    """
    settings = get_settings()

    # Bypass Auth0 when disabled (for testing)
    if settings.auth_disabled:
        logger.warning("Auth0 disabled - using mock test user")
        return {
            "id": "test-user-id",
            "email": "test@themison.com",
            "auth0_sub": "auth0|test-user-id",
        }

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = await verify_auth0_token(token)
    except ValueError as e:
        logger.error("Auth0 token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": payload.get("sub"),
        "email": payload.get("email") or payload.get(
            "https://themison.com/email", ""
        ),
        "auth0_sub": payload.get("sub"),
    }


async def get_current_member(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Member:
    """
    Resolve the Auth0 user to a Member record (carries organization_id for scoping).

    Looks up profiles by email, then members by profile_id.
    Raises 403 if no member record exists.

    If AUTH_DISABLED=true, returns first member in database (for testing).
    """
    settings = get_settings()

    # Bypass member lookup when auth is disabled (for testing)
    if settings.auth_disabled:
        logger.warning("Auth0 disabled - returning first available member")
        result = await db.execute(select(Member).limit(1))
        member = result.scalars().first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No members in database. Create test data first.",
            )
        return member

    email = user.get("email", "")

    # Find profile by email
    result = await db.execute(
        select(Profile).where(Profile.email == email)
    )
    profile = result.scalars().first()

    # --- JIT PROVISIONING START ---
    if not profile:
        logger.info("JIT: Creating new profile for %s", email)
        profile = Profile(
            id=uuid.uuid4(),
            email=email,
            first_name=user.get("name", "").split(" ")[0] if user.get("name") else "New",
            last_name=user.get("name", "").split(" ")[1] if user.get("name") and len(user.get("name").split(" ")) > 1 else "User"
        )
        db.add(profile)
        await db.flush()

    # Find member by profile_id
    result = await db.execute(
        select(Member).where(Member.profile_id == profile.id)
    )
    member = result.scalars().first()

    if not member:
        logger.info("JIT: Creating new membership for %s", email)
        # Ensure a default organization exists
        from app.models.organizations import Organization
        from app.models.themison_admins import ThemisonAdmin

        # 1. Ensure a system admin exists (needed for Organization.created_by)
        admin_result = await db.execute(select(ThemisonAdmin).limit(1))
        admin = admin_result.scalars().first()
        if not admin:
            logger.info("JIT: Creating default system admin")
            admin = ThemisonAdmin(
                id=uuid.uuid4(),
                email="admin@themison.com",
                name="System Admin",
                active=True
            )
            db.add(admin)
            await db.flush()

        # 2. Ensure an organization exists
        org_result = await db.execute(select(Organization).limit(1))
        org = org_result.scalars().first()
        
        if not org:
            logger.info("JIT: Creating default organization")
            org = Organization(
                id=uuid.uuid4(),
                name="Themison Global",
                created_by=admin.id,
                onboarding_completed=True
            )
            db.add(org)
            await db.flush()

        # 3. Create the member
        member = Member(
            id=uuid.uuid4(),
            profile_id=profile.id,
            organization_id=org.id,
            email=email,
            name=user.get("name") or f"{profile.first_name or ''} {profile.last_name or ''}".strip() or email,
            default_role="admin", # First user or new users get admin in this dev stage
            is_active=True,
            onboarding_completed=True
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
    # --- JIT PROVISIONING END ---

    return member


async def get_current_user_id(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """Return just the current user's Auth0 sub claim."""
    return current_user["id"]
