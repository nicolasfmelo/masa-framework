from typing import Protocol

from src.domain.entities.task import Task


class TaskRepository(Protocol):
    def save(self, task: Task) -> Task: ...

    def get_by_id(self, task_id: str) -> Task: ...

    def list_all(self) -> list[Task]: ...
