from dataclasses import dataclass
from typing import Literal

from src.domain_models.ids import AssigneeId, TaskId
from src.domain_models.notification_policy import NotificationPolicy


TaskStatus = Literal["draft", "scheduled", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Task:
    id: TaskId
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee_id: AssigneeId | None
    estimated_minutes: int
    notification_policy: NotificationPolicy
