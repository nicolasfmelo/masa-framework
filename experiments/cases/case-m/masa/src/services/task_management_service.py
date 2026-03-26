from src.domain_models.ids import TaskId
from src.domain_models.task import Task
from src.engines.task_priority_engine import apply_priority, recommend_priority
from src.integrations.database.repos.task_repo import TaskRepository


class TaskManagementService:
    def __init__(self, task_repo: TaskRepository):
        self._task_repo = task_repo

    def create_task(self, task: Task) -> Task:
        priority = recommend_priority(task.estimated_minutes, task.assignee_id is not None)
        prioritized = apply_priority(task, priority)
        return self._task_repo.save(prioritized)

    def update_task(self, task_id: TaskId, updated_task: Task) -> Task:
        self._task_repo.find_by_id(task_id)
        return self._task_repo.save(updated_task)

    def list_tasks(self) -> list[Task]:
        return self._task_repo.list_all()
