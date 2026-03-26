from typing import Protocol

from src.domain.entities.schedule import Schedule


class ScheduleRepository(Protocol):
    def save(self, schedule: Schedule) -> Schedule: ...

    def find_for_task(self, task_id: str) -> Schedule | None: ...
