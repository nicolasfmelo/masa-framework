from src.domain.entities.schedule import Schedule


class InMemoryScheduleRepository:
    def __init__(self, storage: dict[str, Schedule]):
        self._storage = storage

    def save(self, schedule: Schedule) -> Schedule:
        self._storage[schedule.task_id] = schedule
        return schedule

    def find_for_task(self, task_id: str) -> Schedule | None:
        return self._storage.get(task_id)
