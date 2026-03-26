from fastapi import FastAPI

from src.delivery.http.task_management_handler import router, wire_services
from src.domain_models.assignee import Assignee
from src.domain_models.ids import AssigneeId
from src.integrations.database.repos.assignee_repo import AssigneeRepository
from src.integrations.database.repos.schedule_repo import ScheduleRepository
from src.integrations.database.repos.task_repo import TaskRepository
from src.integrations.external_apis.notification_gateway import NotificationGateway
from src.services.task_assignment_service import TaskAssignmentService
from src.services.task_management_service import TaskManagementService
from src.services.task_scheduling_service import TaskSchedulingService

task_storage = {}
assignee_storage = {
    "assignee-1": Assignee(
        id=AssigneeId("assignee-1"),
        name="Alex Johnson",
        email="alex@example.com",
        timezone="UTC",
    )
}
schedule_storage = {}

task_repo = TaskRepository(task_storage)
assignee_repo = AssigneeRepository(assignee_storage)
schedule_repo = ScheduleRepository(schedule_storage)
notification_gateway = NotificationGateway()

task_management_service = TaskManagementService(task_repo=task_repo)
task_assignment_service = TaskAssignmentService(
    task_repo=task_repo,
    assignee_repo=assignee_repo,
)
task_scheduling_service = TaskSchedulingService(
    task_repo=task_repo,
    assignee_repo=assignee_repo,
    schedule_repo=schedule_repo,
    notification_gateway=notification_gateway,
)

wire_services(
    task_management_service=task_management_service,
    task_assignment_service=task_assignment_service,
    task_scheduling_service=task_scheduling_service,
)

app = FastAPI(title="Task Management + Scheduling API")
app.include_router(router)
