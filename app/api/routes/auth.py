"""
Authentication routes
"""

from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.themison_admins import ThemisonAdmin

from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.members import Member
from app.models.profiles import Profile
from app.models.invitations import Invitation
from app.contracts.auth import SignupCompleteRequest, SignupCompleteResponse
from app.core.auth0_management import auth0_mgmt
import uuid
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me")
async def get_me(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the current user's profile, member, and organization data.
    """
    # Eagerly load related profile and organization
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.profiles import Profile
    from app.models.organizations import Organization

    profile = (
        (await db.execute(select(Profile).where(Profile.id == member.profile_id)))
        .scalars()
        .first()
    )

    organization = (
        (
            await db.execute(
                select(Organization).where(Organization.id == member.organization_id)
            )
        )
        .scalars()
        .first()
    )

    return {
        "id": str(member.profile_id),
        "email": member.email,
        "member": {
            "id": str(member.id),
            "name": member.name,
            "email": member.email,
            "organization_id": str(member.organization_id),
            "default_role": member.default_role,
            "onboarding_completed": bool(member.onboarding_completed),
        },
        "profile": {
            "id": str(profile.id) if profile else None,
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "email": profile.email if profile else None,
        },
        "organization": (
            {
                "id": str(organization.id) if organization else None,
                "name": organization.name if organization else None,
                "onboarding_completed": (
                    bool(organization.onboarding_completed) if organization else False
                ),
                "support_enabled": (
                    bool(organization.support_enabled) if organization else True
                ),
            }
            if organization
            else None
        ),
    }


@router.post("/signup/complete", response_model=SignupCompleteResponse)
async def signup_complete(
    payload: SignupCompleteRequest, db: AsyncSession = Depends(get_db)
):
    """
    Finalize signup for an invited user.
    1. Validate token
    2. Create Auth0 user
    3. Create Profile and Member in DB
    4. Mark invitation as accepted
    """
    from sqlalchemy import select

    # 1. Validate Invitation
    result = await db.execute(
        select(Invitation).where(Invitation.token == payload.token)
    )
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.status != "pending":
        raise HTTPException(
            status_code=400, detail="Invitation already used or expired"
        )

    # Check expiration
    from datetime import timezone

    if invitation.expires_at and invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # 2. Create Auth0 User
    try:
        # If names provided in payload, use them, otherwise use invitation name
        display_name = invitation.name
        if payload.first_name and payload.last_name:
            display_name = f"{payload.first_name} {payload.last_name}"

        auth0_user = await auth0_mgmt.create_user(
            email=invitation.email, password=payload.password, name=display_name
        )
        auth0_sub = auth0_user["user_id"]
    except Exception as e:
        logger.error(f"Failed to create Auth0 user: {e}")
        raise HTTPException(
            status_code=500, detail=f"Authentication provider error: {str(e)}"
        )
    # Check if member already exists
    existing_member = (
        (await db.execute(select(Member).where(Member.email == invitation.email)))
        .scalars()
        .first()
    )

    if existing_member:
        # Member already exists — just mark invitation as accepted
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(timezone.utc)
        await db.commit()
        return SignupCompleteResponse(
            success=True,
            message="Signup completed successfully",
            user_id=str(existing_member.profile_id),
        )

    # 3. Create DB Records
    try:
        # Profile
        profile_id = uuid.uuid4()
        # Safe name splitting
        name_parts = invitation.name.split(" ") if invitation.name else ["New", "User"]
        inv_first = name_parts[0]
        inv_last = name_parts[1] if len(name_parts) > 1 else "User"

        new_profile = Profile(
            id=profile_id,
            email=invitation.email,
            first_name=payload.first_name or inv_first,
            last_name=payload.last_name or inv_last,
        )
        db.add(new_profile)

        # Member
        new_member = Member(
            id=uuid.uuid4(),
            name=display_name,
            email=invitation.email,
            organization_id=invitation.organization_id,
            profile_id=profile_id,
            default_role=invitation.initial_role,
            is_active=True,
            onboarding_completed=False,
        )
        db.add(new_member)

        # Auto-create themison_admin for staff members

        if invitation.initial_role == "staff":
            new_admin = ThemisonAdmin(
                email=invitation.email,
                name=display_name,
                active=True,
            )
            db.add(new_admin)

        # 4. Update Invitation
        invitation.status = "accepted"
        from datetime import timezone

        invitation.accepted_at = datetime.now(timezone.utc)

        await db.commit()

        return SignupCompleteResponse(
            success=True,
            message="Signup completed successfully",
            user_id=str(profile_id),
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Signup DB commit failed: {e}")
        raise HTTPException(
            status_code=500, detail="Database error during signup completion"
        )
