from src.domain.entities.schedule import Schedule
from src.domain.entities.task import Task
from src.domain.errors import InvalidScheduleError, NotificationPolicyConflictError


def build_schedule(schedule_id: str, task: Task, due_at: int, reminder_at: int) -> Schedule:
    if due_at <= 0 or reminder_at <= 0:
        raise InvalidScheduleError("due_at and reminder_at must be positive unix timestamps.")
    if reminder_at >= due_at:
        raise InvalidScheduleError("reminder_at must happen before due_at.")

    return Schedule(
        id=schedule_id,
        task_id=task.id,
        due_at=due_at,
        reminder_at=reminder_at,
    )


def ensure_policy_allows(task: Task, schedule: Schedule) -> None:
    minutes_until_due = (schedule.due_at - schedule.reminder_at) // 60
    if task.notification_policy.remind_before_minutes > minutes_until_due:
        raise NotificationPolicyConflictError(
            "Notification policy requests a reminder earlier than the schedule allows."
        )
