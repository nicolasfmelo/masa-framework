from src.application.interfaces.assignee_repository import AssigneeRepository
from src.application.interfaces.notification_dispatcher import NotificationDispatcher
from src.application.interfaces.schedule_repository import ScheduleRepository
from src.application.interfaces.task_repository import TaskRepository
from src.domain.entities.schedule import Schedule
from src.domain.services.schedule_policy import build_schedule, ensure_policy_allows


class ScheduleTaskUseCase:
    def __init__(
        self,
        task_repository: TaskRepository,
        assignee_repository: AssigneeRepository,
        schedule_repository: ScheduleRepository,
        notification_dispatcher: NotificationDispatcher,
    ):
        self._task_repository = task_repository
        self._assignee_repository = assignee_repository
        self._schedule_repository = schedule_repository
        self._notification_dispatcher = notification_dispatcher

    def execute(self, schedule_id: str, task_id: str, due_at: int, reminder_at: int) -> Schedule:
        task = self._task_repository.get_by_id(task_id)
        schedule = build_schedule(schedule_id, task, due_at, reminder_at)
        ensure_policy_allows(task, schedule)
        saved_schedule = self._schedule_repository.save(schedule)

        if task.assignee_id is not None and task.notification_policy.send_on_assignment:
            assignee = self._assignee_repository.get_by_id(task.assignee_id)
            self._notification_dispatcher.schedule_notification(task, assignee, saved_schedule)

        return saved_schedule
