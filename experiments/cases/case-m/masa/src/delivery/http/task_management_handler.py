from fastapi import APIRouter, HTTPException

from src.delivery.schemas.task_schemas import (
    AssignTaskRequestSchema,
    CreateTaskRequestSchema,
    ScheduleResponseSchema,
    ScheduleTaskRequestSchema,
    TaskResponseSchema,
    UpdateTaskRequestSchema,
)
from src.domain_models.assignee import Assignee
from src.domain_models.exceptions import (
    AssigneeNotFoundError,
    InvalidScheduleError,
    NotificationPolicyConflictError,
    TaskNotFoundError,
)
from src.domain_models.ids import AssigneeId, ScheduleId, TaskId
from src.domain_models.notification_policy import NotificationPolicy
from src.domain_models.task import Task
from src.services.task_assignment_service import TaskAssignmentService
from src.services.task_management_service import TaskManagementService
from src.services.task_scheduling_service import TaskSchedulingService

router = APIRouter()

_task_management_service: TaskManagementService | None = None
_task_assignment_service: TaskAssignmentService | None = None
_task_scheduling_service: TaskSchedulingService | None = None


def wire_services(
    task_management_service: TaskManagementService,
    task_assignment_service: TaskAssignmentService,
    task_scheduling_service: TaskSchedulingService,
) -> None:
    global _task_management_service, _task_assignment_service, _task_scheduling_service
    _task_management_service = task_management_service
    _task_assignment_service = task_assignment_service
    _task_scheduling_service = task_scheduling_service


def _require_services() -> tuple[TaskManagementService, TaskAssignmentService, TaskSchedulingService]:
    if _task_management_service is None or _task_assignment_service is None or _task_scheduling_service is None:
        raise RuntimeError("Services are not wired.")
    return _task_management_service, _task_assignment_service, _task_scheduling_service


def _to_task_response(task: Task) -> TaskResponseSchema:
    return TaskResponseSchema(
        id=task.id.value,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assignee_id=task.assignee_id.value if task.assignee_id else None,
        estimated_minutes=task.estimated_minutes,
        notification_channel=task.notification_policy.channel,
        remind_before_minutes=task.notification_policy.remind_before_minutes,
        send_on_assignment=task.notification_policy.send_on_assignment,
    )


@router.post("/tasks", response_model=TaskResponseSchema)
def create_task(request: CreateTaskRequestSchema) -> TaskResponseSchema:
    task_management_service, _, _ = _require_services()

    task = Task(
        id=TaskId(request.id),
        title=request.title,
        description=request.description,
        status="draft",
        priority="low",
        assignee_id=None,
        estimated_minutes=request.estimated_minutes,
        notification_policy=NotificationPolicy(
            channel=request.notification_policy.channel,  # type: ignore[arg-type]
            remind_before_minutes=request.notification_policy.remind_before_minutes,
            send_on_assignment=request.notification_policy.send_on_assignment,
        ),
    )
    created = task_management_service.create_task(task)
    return _to_task_response(created)


@router.get("/tasks", response_model=list[TaskResponseSchema])
def list_tasks() -> list[TaskResponseSchema]:
    task_management_service, _, _ = _require_services()
    return [_to_task_response(task) for task in task_management_service.list_tasks()]


@router.put("/tasks/{task_id}", response_model=TaskResponseSchema)
def update_task(task_id: str, request: UpdateTaskRequestSchema) -> TaskResponseSchema:
    task_management_service, _, _ = _require_services()

    existing = next((task for task in task_management_service.list_tasks() if task.id.value == task_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")

    updated = Task(
        id=existing.id,
        title=request.title,
        description=request.description,
        status=request.status,  # type: ignore[arg-type]
        priority=existing.priority,
        assignee_id=existing.assignee_id,
        estimated_minutes=request.estimated_minutes,
        notification_policy=existing.notification_policy,
    )
    saved = task_management_service.update_task(existing.id, updated)
    return _to_task_response(saved)


@router.post("/tasks/{task_id}/assign", response_model=TaskResponseSchema)
def assign_task(task_id: str, request: AssignTaskRequestSchema) -> TaskResponseSchema:
    _, task_assignment_service, _ = _require_services()
    try:
        assigned = task_assignment_service.assign(TaskId(task_id), AssigneeId(request.assignee_id))
    except (TaskNotFoundError, AssigneeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_task_response(assigned)


@router.post("/tasks/{task_id}/schedule", response_model=ScheduleResponseSchema)
def schedule_task(task_id: str, request: ScheduleTaskRequestSchema) -> ScheduleResponseSchema:
    _, _, task_scheduling_service = _require_services()
    try:
        schedule = task_scheduling_service.schedule_task(
            schedule_id=ScheduleId(request.schedule_id),
            task_id=TaskId(task_id),
            due_at=request.due_at,
            reminder_at=request.reminder_at,
        )
    except (TaskNotFoundError, AssigneeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (InvalidScheduleError, NotificationPolicyConflictError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ScheduleResponseSchema(
        id=schedule.id.value,
        task_id=schedule.task_id.value,
        due_at=schedule.due_at,
        reminder_at=schedule.reminder_at,
    )
