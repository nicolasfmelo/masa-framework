from src.domain_models.ids import AssigneeId, TaskId
from src.domain_models.task import Task
from src.integrations.database.repos.assignee_repo import AssigneeRepository
from src.integrations.database.repos.task_repo import TaskRepository


class TaskAssignmentService:
    def __init__(self, task_repo: TaskRepository, assignee_repo: AssigneeRepository):
        self._task_repo = task_repo
        self._assignee_repo = assignee_repo

    def assign(self, task_id: TaskId, assignee_id: AssigneeId) -> Task:
        task = self._task_repo.find_by_id(task_id)
        self._assignee_repo.find_by_id(assignee_id)
        assigned = Task(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            assignee_id=assignee_id,
            estimated_minutes=task.estimated_minutes,
            notification_policy=task.notification_policy,
        )
        return self._task_repo.save(assigned)
