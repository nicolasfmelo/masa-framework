from src.domain_models.task import Task, TaskPriority


def recommend_priority(estimated_minutes: int, has_assignee: bool) -> TaskPriority:
    if estimated_minutes >= 240:
        return "high"
    if estimated_minutes >= 90 or not has_assignee:
        return "medium"
    return "low"


def apply_priority(task: Task, priority: TaskPriority) -> Task:
    return Task(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=priority,
        assignee_id=task.assignee_id,
        estimated_minutes=task.estimated_minutes,
        notification_policy=task.notification_policy,
    )
