from src.application.interfaces.task_repository import TaskRepository
from src.domain.entities.task import Task


class UpdateTaskUseCase:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository

    def execute(self, task_id: str, title: str, description: str, status: str, estimated_minutes: int) -> Task:
        current_task = self._task_repository.get_by_id(task_id)
        updated_task = Task(
            id=current_task.id,
            title=title,
            description=description,
            status=status,
            priority=current_task.priority,
            assignee_id=current_task.assignee_id,
            estimated_minutes=estimated_minutes,
            notification_policy=current_task.notification_policy,
        )
        return self._task_repository.save(updated_task)
