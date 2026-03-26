from src.domain.entities.assignee import Assignee
from src.domain.entities.schedule import Schedule
from src.domain.entities.task import Task


class InMemoryNotificationDispatcher:
    def __init__(self):
        self._events: list[dict[str, str | int]] = []

    def schedule_notification(self, task: Task, assignee: Assignee, schedule: Schedule) -> None:
        self._events.append(
            {
                "task_id": task.id,
                "assignee_id": assignee.id,
                "channel": task.notification_policy.channel,
                "reminder_at": schedule.reminder_at,
            }
        )

    def list_events(self) -> list[dict[str, str | int]]:
        return list(self._events)
