from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.tasks import Task
from app.models.members import Member
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_member
from app.contracts.tasks import TaskResponse, TaskCreate, TaskUpdate, AssignedUser

router = APIRouter(tags=["tasks"])


# -----------------------
# GET - List Tasks
# -----------------------
@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    trial_id: Optional[UUID] = None,
    patient_id: Optional[UUID] = None,
    assigned_to: Optional[UUID] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).where(Task.deleted_at.is_(None))

    if trial_id:
        stmt = stmt.where(Task.trial_id == trial_id)

    if patient_id:
        stmt = stmt.where(Task.patient_id == patient_id)

    if assigned_to:
        stmt = stmt.where(Task.assigned_to == assigned_to)

    if status:
        stmt = stmt.where(Task.status == status)

    if priority:
        stmt = stmt.where(Task.priority == priority)

    if category:
        stmt = stmt.where(Task.category == category)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    tasks_with_user = []

    for task in tasks:
        assigned_user = None

        if task.assigned_to:
            user = await db.get(Member, task.assigned_to)
            if user:
                assigned_user = AssignedUser(id=user.id, full_name=user.full_name)

        tasks_with_user.append(
            TaskResponse(
                id=task.id,
                trial_id=task.trial_id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                category=task.category,
                due_date=task.due_date,
                assigned_to=task.assigned_to,
                assigned_user=assigned_user,
                patient_id=task.patient_id,
                visit_id=task.visit_id,
                activity_type_id=task.activity_type_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )

    return tasks_with_user


# -----------------------
# POST - Create Task
# -----------------------
@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    payload: TaskCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    task = Task(**payload.model_dump(), created_by=member.id)

    db.add(task)
    await db.commit()
    await db.refresh(task)

    assigned_user = None

    if task.assigned_to:
        user = await db.get(Member, task.assigned_to)
        if user:
            assigned_user = AssignedUser(id=user.id, full_name=user.full_name)

    return TaskResponse(
        id=task.id,
        trial_id=task.trial_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        category=task.category,
        due_date=task.due_date,
        assigned_to=task.assigned_to,
        assigned_user=assigned_user,
        patient_id=task.patient_id,
        visit_id=task.visit_id,
        activity_type_id=task.activity_type_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# -----------------------
# PATCH - Update Task
# -----------------------
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):

    task = await db.get(Task, task_id)

    if not task or task.deleted_at:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)

    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    assigned_user = None

    if task.assigned_to:
        user = await db.get(Member, task.assigned_to)
        if user:
            assigned_user = AssignedUser(id=user.id, full_name=user.full_name)

    return TaskResponse(
        id=task.id,
        trial_id=task.trial_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        category=task.category,
        due_date=task.due_date,
        assigned_to=task.assigned_to,
        assigned_user=assigned_user,
        patient_id=task.patient_id,
        visit_id=task.visit_id,
        activity_type_id=task.activity_type_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# -----------------------
# DELETE - Soft Delete
# -----------------------
@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):

    task = await db.get(Task, task_id)

    if not task or task.deleted_at:
        raise HTTPException(status_code=404, detail="Task not found")

    task.deleted_at = datetime.utcnow()

    await db.commit()

    return {"success": True}
