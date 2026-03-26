from dataclasses import dataclass

from src.domain_models.ids import ScheduleId, TaskId


@dataclass(frozen=True)
class Schedule:
    id: ScheduleId
    task_id: TaskId
    due_at: int
    reminder_at: int
