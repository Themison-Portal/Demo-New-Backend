# app/api/routes/api/task_dependencies.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_dependencies import TaskDependency
from app.models.tasks import Task
from app.models.members import Member
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_member
from app.contracts.task_dependencies import TaskDependencyResponse, TaskDependencyCreate

router = APIRouter(tags=["task-dependencies"])


@router.get("/", response_model=List[TaskDependencyResponse])
async def list_dependencies(
    task_id: Optional[UUID] = None,
    trial_id: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TaskDependency)

    if task_id:
        stmt = stmt.where(
            or_(
                TaskDependency.source_task_id == task_id,
                TaskDependency.target_task_id == task_id
            )
        )

    if trial_id:
        stmt = stmt.join(Task, TaskDependency.source_task_id == Task.id).where(Task.trial_id == trial_id)

    result = await db.execute(stmt)
    deps = result.scalars().all()
    return deps


@router.post("/", response_model=TaskDependencyResponse, status_code=201)
async def create_dependency(
    payload: TaskDependencyCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Task, payload.source_task_id)
    target = await db.get(Task, payload.target_task_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target task not found")

    dep = TaskDependency(**payload.model_dump())
    db.add(dep)
    await db.commit()
    await db.refresh(dep)
    return dep


@router.delete("/{dependency_id}")
async def delete_dependency(
    dependency_id: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    dep = await db.get(TaskDependency, dependency_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")

    await db.delete(dep)
    await db.commit()
    return {"success": True}
