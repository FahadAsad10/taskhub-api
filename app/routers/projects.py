from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession, OwnedProject
from app.models import Project, Task, TaskStatus
from app.schemas import Page, ProjectCreate, ProjectOut, ProjectStats, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectOut])
def list_projects(
    db: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    query = select(Project).where(Project.owner_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Project.created_at.desc(), Project.id.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: DbSession, user: CurrentUser) -> Project:
    project = Project(**body.model_dump(), owner_id=user.id)
    db.add(project)
    db.commit()
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: OwnedProject) -> Project:
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(body: ProjectUpdate, project: OwnedProject, db: DbSession) -> Project:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: OwnedProject, db: DbSession) -> None:
    db.delete(project)
    db.commit()


@router.get("/{project_id}/stats", response_model=ProjectStats)
def project_stats(project: OwnedProject, db: DbSession) -> ProjectStats:
    rows = db.execute(
        select(Task.status, func.count()).where(Task.project_id == project.id).group_by(Task.status)
    ).all()
    counts = {s: 0 for s in TaskStatus}
    counts.update({s: n for s, n in rows})
    overdue = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.project_id == project.id, Task.status != TaskStatus.done, Task.due_date < date.today())
    )
    total = sum(counts.values())
    return ProjectStats(
        total=total,
        todo=counts[TaskStatus.todo],
        in_progress=counts[TaskStatus.in_progress],
        done=counts[TaskStatus.done],
        overdue=overdue or 0,
        completion_rate=round(counts[TaskStatus.done] / total, 2) if total else 0.0,
    )
