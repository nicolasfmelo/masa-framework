from src.domain_models.ids import ScheduleId, TaskId
from src.domain_models.schedule import Schedule
from src.domain_models.task import Task
from src.engines.notification_policy_engine import validate_notification_policy
from src.engines.schedule_window_engine import build_schedule
from src.integrations.database.repos.assignee_repo import AssigneeRepository
from src.integrations.database.repos.schedule_repo import ScheduleRepository
from src.integrations.database.repos.task_repo import TaskRepository
from src.integrations.external_apis.notification_gateway import NotificationGateway


class TaskSchedulingService:
    def __init__(
        self,
        task_repo: TaskRepository,
        assignee_repo: AssigneeRepository,
        schedule_repo: ScheduleRepository,
        notification_gateway: NotificationGateway,
    ):
        self._task_repo = task_repo
        self._assignee_repo = assignee_repo
        self._schedule_repo = schedule_repo
        self._notification_gateway = notification_gateway

    def schedule_task(self, schedule_id: ScheduleId, task_id: TaskId, due_at: int, reminder_at: int) -> Schedule:
        task = self._task_repo.find_by_id(task_id)
        schedule = build_schedule(schedule_id, task, due_at, reminder_at)
        validate_notification_policy(task.notification_policy, schedule)
        saved = self._schedule_repo.save(schedule)

        if task.assignee_id is not None and task.notification_policy.send_on_assignment:
            assignee = self._assignee_repo.find_by_id(task.assignee_id)
            self._notification_gateway.schedule_notification(
                task=task,
                assignee=assignee,
                schedule=saved,
                policy=task.notification_policy,
            )

        return saved
