from dataclasses import dataclass

from src.domain.value_objects.notification_policy import NotificationPolicy

VALID_STATUSES = {"draft", "scheduled", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    description: str
    status: str
    priority: str
    assignee_id: str | None
    estimated_minutes: int
    notification_policy: NotificationPolicy

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid task status: {self.status}")
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid task priority: {self.priority}")
