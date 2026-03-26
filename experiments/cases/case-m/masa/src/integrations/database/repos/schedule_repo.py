from src.domain_models.ids import TaskId
from src.domain_models.schedule import Schedule


class ScheduleRepository:
    def __init__(self, storage: dict[str, Schedule]):
        self._storage = storage

    def save(self, schedule: Schedule) -> Schedule:
        self._storage[schedule.task_id.value] = schedule
        return schedule

    def find_for_task(self, task_id: TaskId) -> Schedule | None:
        return self._storage.get(task_id.value)
