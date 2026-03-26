from src.application.interfaces.assignee_repository import AssigneeRepository
from src.application.interfaces.task_repository import TaskRepository
from src.domain.entities.task import Task


class AssignTaskUseCase:
    def __init__(self, task_repository: TaskRepository, assignee_repository: AssigneeRepository):
        self._task_repository = task_repository
        self._assignee_repository = assignee_repository

    def execute(self, task_id: str, assignee_id: str) -> Task:
        current_task = self._task_repository.get_by_id(task_id)
        self._assignee_repository.get_by_id(assignee_id)
        assigned_task = Task(
            id=current_task.id,
            title=current_task.title,
            description=current_task.description,
            status=current_task.status,
            priority=current_task.priority,
            assignee_id=assignee_id,
            estimated_minutes=current_task.estimated_minutes,
            notification_policy=current_task.notification_policy,
        )
        return self._task_repository.save(assigned_task)
