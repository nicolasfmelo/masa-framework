from fastapi import APIRouter, HTTPException

from src.application.use_cases.assign_task import AssignTaskUseCase
from src.application.use_cases.create_task import CreateTaskUseCase
from src.application.use_cases.list_tasks import ListTasksUseCase
from src.application.use_cases.schedule_task import ScheduleTaskUseCase
from src.application.use_cases.update_task import UpdateTaskUseCase
from src.domain.entities.task import Task
from src.domain.errors import (
    AssigneeNotFoundError,
    InvalidScheduleError,
    NotificationPolicyConflictError,
    TaskNotFoundError,
)
from src.domain.value_objects.notification_policy import NotificationPolicy
from src.presentation.http.task_schemas import (
    AssignTaskRequestSchema,
    CreateTaskRequestSchema,
    ScheduleResponseSchema,
    ScheduleTaskRequestSchema,
    TaskResponseSchema,
    UpdateTaskRequestSchema,
)

router = APIRouter()

_create_task_use_case: CreateTaskUseCase | None = None
_list_tasks_use_case: ListTasksUseCase | None = None
_update_task_use_case: UpdateTaskUseCase | None = None
_assign_task_use_case: AssignTaskUseCase | None = None
_schedule_task_use_case: ScheduleTaskUseCase | None = None


def wire_use_cases(
    *,
    create_task_use_case: CreateTaskUseCase,
    list_tasks_use_case: ListTasksUseCase,
    update_task_use_case: UpdateTaskUseCase,
    assign_task_use_case: AssignTaskUseCase,
    schedule_task_use_case: ScheduleTaskUseCase,
) -> None:
    global _create_task_use_case, _list_tasks_use_case, _update_task_use_case
    global _assign_task_use_case, _schedule_task_use_case
    _create_task_use_case = create_task_use_case
    _list_tasks_use_case = list_tasks_use_case
    _update_task_use_case = update_task_use_case
    _assign_task_use_case = assign_task_use_case
    _schedule_task_use_case = schedule_task_use_case


def _require_use_cases() -> tuple[
    CreateTaskUseCase,
    ListTasksUseCase,
    UpdateTaskUseCase,
    AssignTaskUseCase,
    ScheduleTaskUseCase,
]:
    if None in (
        _create_task_use_case,
        _list_tasks_use_case,
        _update_task_use_case,
        _assign_task_use_case,
        _schedule_task_use_case,
    ):
        raise RuntimeError("Use cases are not wired.")

    return (
        _create_task_use_case,
        _list_tasks_use_case,
        _update_task_use_case,
        _assign_task_use_case,
        _schedule_task_use_case,
    )


def _to_task_response(task: Task) -> TaskResponseSchema:
    return TaskResponseSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assignee_id=task.assignee_id,
        estimated_minutes=task.estimated_minutes,
        notification_channel=task.notification_policy.channel,
        remind_before_minutes=task.notification_policy.remind_before_minutes,
        send_on_assignment=task.notification_policy.send_on_assignment,
    )


@router.post("/tasks", response_model=TaskResponseSchema)
def create_task(request: CreateTaskRequestSchema) -> TaskResponseSchema:
    create_task_use_case, _, _, _, _ = _require_use_cases()
    task = Task(
        id=request.id,
        title=request.title,
        description=request.description,
        status="draft",
        priority="low",
        assignee_id=None,
        estimated_minutes=request.estimated_minutes,
        notification_policy=NotificationPolicy(
            channel=request.notification_policy.channel,
            remind_before_minutes=request.notification_policy.remind_before_minutes,
            send_on_assignment=request.notification_policy.send_on_assignment,
        ),
    )
    return _to_task_response(create_task_use_case.execute(task))


@router.get("/tasks", response_model=list[TaskResponseSchema])
def list_tasks() -> list[TaskResponseSchema]:
    _, list_tasks_use_case, _, _, _ = _require_use_cases()
    return [_to_task_response(task) for task in list_tasks_use_case.execute()]


@router.put("/tasks/{task_id}", response_model=TaskResponseSchema)
def update_task(task_id: str, request: UpdateTaskRequestSchema) -> TaskResponseSchema:
    _, _, update_task_use_case, _, _ = _require_use_cases()
    try:
        task = update_task_use_case.execute(
            task_id=task_id,
            title=request.title,
            description=request.description,
            status=request.status,
            estimated_minutes=request.estimated_minutes,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_task_response(task)


@router.post("/tasks/{task_id}/assign", response_model=TaskResponseSchema)
def assign_task(task_id: str, request: AssignTaskRequestSchema) -> TaskResponseSchema:
    _, _, _, assign_task_use_case, _ = _require_use_cases()
    try:
        task = assign_task_use_case.execute(task_id=task_id, assignee_id=request.assignee_id)
    except (TaskNotFoundError, AssigneeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_task_response(task)


@router.post("/tasks/{task_id}/schedule", response_model=ScheduleResponseSchema)
def schedule_task(task_id: str, request: ScheduleTaskRequestSchema) -> ScheduleResponseSchema:
    _, _, _, _, schedule_task_use_case = _require_use_cases()
    try:
        schedule = schedule_task_use_case.execute(
            schedule_id=request.schedule_id,
            task_id=task_id,
            due_at=request.due_at,
            reminder_at=request.reminder_at,
        )
    except (TaskNotFoundError, AssigneeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (InvalidScheduleError, NotificationPolicyConflictError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ScheduleResponseSchema(
        id=schedule.id,
        task_id=schedule.task_id,
        due_at=schedule.due_at,
        reminder_at=schedule.reminder_at,
    )
