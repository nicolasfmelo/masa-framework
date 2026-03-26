from typing import Protocol

from src.domain.entities.assignee import Assignee
from src.domain.entities.schedule import Schedule
from src.domain.entities.task import Task


class NotificationDispatcher(Protocol):
    def schedule_notification(self, task: Task, assignee: Assignee, schedule: Schedule) -> None: ...
