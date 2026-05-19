"""
Invitation routes — GET /count, POST /batch

Invitation token validation — GET /invitations/validate/{token}
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from datetime import datetime, timezone, timedelta

from app.contracts.invitation import (
    InvitationBatchCreate,
    InvitationCountResponse,
    InvitationResponse,
)
from app.dependencies.auth import get_current_member
from app.dependencies.db import get_db
from app.models.invitations import Invitation
from app.models.members import Member
from app.models.organizations import Organization
from app.services.email_service import email_service

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[InvitationResponse])
async def list_invitations(
    status: str = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    org_id = member.organization_id
    query = select(Invitation).where(Invitation.organization_id == org_id)

    if status:
        query = query.where(Invitation.status == status)

    query = query.order_by(Invitation.invited_at.desc())

    result = await db.execute(query)
    invitations = result.scalars().all()
    return [
        {
            "id": inv.id,
            "email": inv.email,
            "name": inv.name,
            "org_role": inv.initial_role,
            "organization_id": inv.organization_id,
            "status": inv.status,
            "invited_by": inv.invited_by,
            "invited_at": inv.invited_at,
            "expires_at": inv.expires_at,
            "accepted_at": inv.accepted_at,
        }
        for inv in invitations
    ]


@router.get("/validate/{token}")
async def validate_invitation_token(token: str, db: AsyncSession = Depends(get_db)):
    """
    Validate an invitation token for signup (new users).

    Returns invitation details if valid.
    Raises 404/400 if token is invalid, expired, already used, or does not exist.
    """
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is not pending (current status: {invitation.status})",
        )

    if invitation.expires_at and invitation.expires_at < datetime.now(timezone.utc):
        # Optionally, mark invitation as expired in DB
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Fetch organization details
    org_result = await db.execute(
        select(Organization).where(Organization.id == invitation.organization_id)
    )
    org = org_result.scalars().first()

    # Format according to Frontend expectations
    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "org_id": str(invitation.organization_id),
        "org_role": invitation.initial_role,
        "organization": {
            "id": str(invitation.organization_id),
            "name": org.name if org else "Themison",
        },
        "name": invitation.name,
        "expires_at": (
            invitation.expires_at.isoformat() if invitation.expires_at else None
        ),
    }


@router.get("/count", response_model=InvitationCountResponse)
async def get_invitation_counts(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    org_id = member.organization_id

    pending = (
        await db.execute(
            select(func.count())
            .select_from(Invitation)
            .where(Invitation.organization_id == org_id, Invitation.status == "pending")
        )
    ).scalar_one()

    accepted = (
        await db.execute(
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.organization_id == org_id, Invitation.status == "accepted"
            )
        )
    ).scalar_one()

    expired = (
        await db.execute(
            select(func.count())
            .select_from(Invitation)
            .where(Invitation.organization_id == org_id, Invitation.status == "expired")
        )
    ).scalar_one()

    return InvitationCountResponse(
        pending=pending,
        accepted=accepted,
        expired=expired,
        total=pending + accepted + expired,
    )


@router.post("/batch", response_model=List[InvitationResponse], status_code=201)
async def batch_create_invitations(
    payload: InvitationBatchCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    org_id = member.organization_id
    created = []

    for item in payload.invitations:
        logger.info(
            f"[TRACE] Processing invitation for: {item.email} (Role: {item.org_role})"
        )
        # Check email uniqueness within org
        existing = (
            (
                await db.execute(
                    select(Invitation).where(
                        Invitation.organization_id == org_id,
                        Invitation.email == item.email,
                        Invitation.status == "pending",
                    )
                )
            )
            .scalars()
            .first()
        )

        if existing:
            # logger.warning(f"[TRACE] Pending invitation already exists for {item.email}")
            # raise HTTPException(
            #     status_code=409,
            #     detail=f"Pending invitation already exists for {item.email}",
            # )

            existing.invited_at = datetime.now(timezone.utc)
            existing.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            existing.initial_role = item.org_role
            existing.invited_by = member.id
            created.append(existing)
            continue

        inv = Invitation(
            email=item.email,
            name=item.name or item.email.split("@")[0],
            organization_id=org_id,
            initial_role=item.org_role,
            invited_by=member.id,
        )
        db.add(inv)
        created.append(inv)
        logger.info(f"[TRACE] Invitation object staged in session for {item.email}")

    # Fetch organization name for the email
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalars().first()
    org_name = org.name if org else "Themison"
    logger.info(
        f"[TRACE] Organization found: {org_name}. Committing database session..."
    )

    try:
        await db.commit()
        logger.info(
            f"[TRACE] Database commit SUCCESSFUL for {len(created)} invitations."
        )
    except Exception as e:
        logger.error(f"[TRACE] Database commit FAILED: {e}")
        await db.rollback()
        raise

    # Refresh and send emails
    for inv in created:
        await db.refresh(inv)
        logger.info(
            f"[TRACE] Dispatching email for {inv.email} with token: {inv.token[:8]}..."
        )
        # Trigger email (asynchronous logs for now)
        sent = await email_service.send_invitation_email(
            email=inv.email, name=inv.name, token=inv.token, org_name=org_name
        )
        logger.info(f"[TRACE] Email service result for {inv.email}: {sent}")

    return created
