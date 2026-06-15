"""
Authentication dependencies — Auth0 JWT verification.
"""

import logging
import uuid
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.auth0 import verify_auth0_token
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.profiles import Profile

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Fixed demo member — used when AUTH_DISABLED=true
DEMO_MEMBER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_PROFILE_ID = UUID("00000000-0000-0000-0000-000000000002")
DEMO_ORG_ID = UUID("00000000-0000-0000-0000-000000000003")


def _make_demo_member() -> Member:
    mock = Member()
    mock.id = DEMO_MEMBER_ID
    mock.profile_id = DEMO_PROFILE_ID
    mock.organization_id = DEMO_ORG_ID
    mock.default_role = "admin"
    mock.name = "Demo User"
    mock.email = "demo@themison.com"
    mock.is_active = True
    mock.onboarding_completed = True
    return mock


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Verify Auth0 JWT and return basic user info.

    Returns dict with ``id`` (profile UUID), ``email``, ``auth0_sub``.

    If X-User-Email is present in headers, returns proxy user details.
    If AUTH_DISABLED=true in .env, returns a mock test user.
    """
    # Check for trusted proxy headers
    x_user_email = request.headers.get("x-user-email")
    if x_user_email:
        x_user_name = (
            request.headers.get("x-user-name") or x_user_email.split("@")[0].title()
        )
        return {
            "id": f"proxy|{x_user_email}",
            "email": x_user_email,
            "auth0_sub": f"proxy|{x_user_email}",
            "name": x_user_name,
        }

    settings = get_settings()

    if settings.auth_disabled:
        logger.warning("Auth0 disabled - using demo user")
        return {
            "id": str(DEMO_PROFILE_ID),
            "email": "demo@themison.com",
            "auth0_sub": "demo|00000000",
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
        "email": payload.get("email") or payload.get("https://themison.com/email", ""),
        "auth0_sub": payload.get("sub"),
        "name": payload.get("name") or payload.get("nickname") or "",
    }


async def get_current_member(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Member:
    settings = get_settings()

    # ── Demo mode — return fixed mock member, no DB needed ──
    if settings.auth_disabled:
        logger.warning("Auth0 disabled - returning demo member")
        return _make_demo_member()

    email = user.get("email", "")

    # Find profile by email
    result = await db.execute(select(Profile).where(Profile.email == email))
    profile = result.scalars().first()

    # --- JIT PROVISIONING START ---
    if not profile:
        logger.info("JIT: Creating new profile for %s", email)
        profile = Profile(
            id=uuid.uuid4(),
            email=email,
            first_name=(
                user.get("name", "").split(" ")[0] if user.get("name") else "New"
            ),
            last_name=(
                user.get("name", "").split(" ")[1]
                if user.get("name") and len(user.get("name").split(" ")) > 1
                else "User"
            ),
        )
        db.add(profile)
        await db.flush()

    # Find member by profile_id
    result = await db.execute(select(Member).where(Member.profile_id == profile.id))
    member = result.scalars().first()

    if not member:
        logger.info("JIT: Creating new membership for %s", email)
        from app.models.organizations import Organization
        from app.models.themison_admins import ThemisonAdmin

        admin_result = await db.execute(select(ThemisonAdmin).limit(1))
        admin = admin_result.scalars().first()
        if not admin:
            logger.info("JIT: Creating default system admin")
            admin = ThemisonAdmin(
                id=uuid.uuid4(),
                email="admin@themison.com",
                name="System Admin",
                active=True,
            )
            db.add(admin)
            await db.flush()

        org_result = await db.execute(select(Organization).limit(1))
        org = org_result.scalars().first()

        if not org:
            logger.info("JIT: Creating default organization")
            org = Organization(
                id=uuid.uuid4(),
                name="Themison Global",
                created_by=admin.id,
                onboarding_completed=True,
            )
            db.add(org)
            await db.flush()

        member = Member(
            id=uuid.uuid4(),
            profile_id=profile.id,
            organization_id=org.id,
            email=email,
            name=user.get("name")
            or f"{profile.first_name or ''} {profile.last_name or ''}".strip()
            or email,
            default_role="admin",
            is_active=True,
            onboarding_completed=True,
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
    # --- JIT PROVISIONING END ---

    return member


async def get_current_user_id(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    return current_user["id"]
