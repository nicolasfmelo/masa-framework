from dataclasses import dataclass


@dataclass(frozen=True)
class Schedule:
    id: str
    task_id: str
    due_at: int
    reminder_at: int
