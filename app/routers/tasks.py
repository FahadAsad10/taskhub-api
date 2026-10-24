from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.deps import DbSession, OwnedProject
from app.models import Task, TaskPriority, TaskStatus
from app.schemas import Page, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])

SORTS = {
    "created": Task.created_at,
    "due": Task.due_date,
    "title": Task.title,
}


def _get_task(db: DbSession, project_id: int, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    project: OwnedProject,
    db: DbSession,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Search in title and description")] = None,
    sort: Literal["created", "due", "title"] = "created",
    order: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    query = select(Task).where(Task.project_id == project.id)
    if status_:
        query = query.where(Task.status == status_)
    if priority:
        query = query.where(Task.priority == priority)
    if q:
        pattern = f"%{q}%"
        query = query.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    column = SORTS[sort]
    query = query.order_by(column.asc() if order == "asc" else column.desc(), Task.id)
    items = db.scalars(query.limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, project: OwnedProject, db: DbSession) -> Task:
    task = Task(**body.model_dump(), project_id=project.id)
    db.add(task)
    db.commit()
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, project: OwnedProject, db: DbSession) -> Task:
    return _get_task(db, project.id, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, project: OwnedProject, db: DbSession) -> Task:
    task = _get_task(db, project.id, task_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, project: OwnedProject, db: DbSession) -> None:
    db.delete(_get_task(db, project.id, task_id))
    db.commit()
