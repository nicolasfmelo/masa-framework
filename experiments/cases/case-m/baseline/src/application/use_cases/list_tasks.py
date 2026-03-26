from src.application.interfaces.task_repository import TaskRepository
from src.domain.entities.task import Task


class ListTasksUseCase:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository

    def execute(self) -> list[Task]:
        return self._task_repository.list_all()
