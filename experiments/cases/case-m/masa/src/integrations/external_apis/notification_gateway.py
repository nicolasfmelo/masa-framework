from src.domain_models.assignee import Assignee
from src.domain_models.notification_policy import NotificationPolicy
from src.domain_models.schedule import Schedule
from src.domain_models.task import Task


class NotificationGateway:
    def __init__(self):
        self._events: list[dict[str, str | int]] = []

    def schedule_notification(
        self,
        task: Task,
        assignee: Assignee,
        schedule: Schedule,
        policy: NotificationPolicy,
    ) -> None:
        self._events.append(
            {
                "task_id": task.id.value,
                "assignee_id": assignee.id.value,
                "channel": policy.channel,
                "reminder_at": schedule.reminder_at,
            }
        )

    def list_events(self) -> list[dict[str, str | int]]:
        return list(self._events)
