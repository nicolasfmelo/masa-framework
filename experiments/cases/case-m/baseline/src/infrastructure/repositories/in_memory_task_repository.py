from src.domain.entities.task import Task
from src.domain.errors import TaskNotFoundError


class InMemoryTaskRepository:
    def __init__(self, storage: dict[str, Task]):
        self._storage = storage

    def save(self, task: Task) -> Task:
        self._storage[task.id] = task
        return task

    def get_by_id(self, task_id: str) -> Task:
        task = self._storage.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found.")
        return task

    def list_all(self) -> list[Task]:
        return list(self._storage.values())
