from src.domain_models.exceptions import TaskNotFoundError
from src.domain_models.ids import TaskId
from src.domain_models.task import Task


class TaskRepository:
    def __init__(self, storage: dict[str, Task]):
        self._storage = storage

    def save(self, task: Task) -> Task:
        self._storage[task.id.value] = task
        return task

    def find_by_id(self, task_id: TaskId) -> Task:
        task = self._storage.get(task_id.value)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id.value} not found.")
        return task

    def list_all(self) -> list[Task]:
        return list(self._storage.values())
