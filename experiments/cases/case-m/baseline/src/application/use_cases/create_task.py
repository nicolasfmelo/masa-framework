from src.application.interfaces.task_repository import TaskRepository
from src.domain.entities.task import Task
from src.domain.services.task_priority_policy import recommend_priority, with_priority


class CreateTaskUseCase:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository

    def execute(self, task: Task) -> Task:
        priority = recommend_priority(task.estimated_minutes, task.assignee_id is not None)
        prioritized_task = with_priority(task, priority)
        return self._task_repository.save(prioritized_task)
