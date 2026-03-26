from fastapi import FastAPI

from src.application.use_cases.assign_task import AssignTaskUseCase
from src.application.use_cases.create_task import CreateTaskUseCase
from src.application.use_cases.list_tasks import ListTasksUseCase
from src.application.use_cases.schedule_task import ScheduleTaskUseCase
from src.application.use_cases.update_task import UpdateTaskUseCase
from src.domain.entities.assignee import Assignee
from src.infrastructure.notifications.in_memory_notification_dispatcher import (
    InMemoryNotificationDispatcher,
)
from src.infrastructure.repositories.in_memory_assignee_repository import (
    InMemoryAssigneeRepository,
)
from src.infrastructure.repositories.in_memory_schedule_repository import (
    InMemoryScheduleRepository,
)
from src.infrastructure.repositories.in_memory_task_repository import InMemoryTaskRepository
from src.presentation.http.task_controller import router, wire_use_cases

task_storage = {}
assignee_storage = {
    "assignee-1": Assignee(
        id="assignee-1",
        name="Alex Johnson",
        email="alex@example.com",
        timezone="UTC",
    )
}
schedule_storage = {}

task_repository = InMemoryTaskRepository(task_storage)
assignee_repository = InMemoryAssigneeRepository(assignee_storage)
schedule_repository = InMemoryScheduleRepository(schedule_storage)
notification_dispatcher = InMemoryNotificationDispatcher()

create_task_use_case = CreateTaskUseCase(task_repository)
list_tasks_use_case = ListTasksUseCase(task_repository)
update_task_use_case = UpdateTaskUseCase(task_repository)
assign_task_use_case = AssignTaskUseCase(task_repository, assignee_repository)
schedule_task_use_case = ScheduleTaskUseCase(
    task_repository,
    assignee_repository,
    schedule_repository,
    notification_dispatcher,
)

wire_use_cases(
    create_task_use_case=create_task_use_case,
    list_tasks_use_case=list_tasks_use_case,
    update_task_use_case=update_task_use_case,
    assign_task_use_case=assign_task_use_case,
    schedule_task_use_case=schedule_task_use_case,
)

app = FastAPI(title="Task Management + Scheduling API")
app.include_router(router)


def notification_events() -> list[dict[str, str | int]]:
    return notification_dispatcher.list_events()


def task_listing():
    return list_tasks_use_case.execute()
