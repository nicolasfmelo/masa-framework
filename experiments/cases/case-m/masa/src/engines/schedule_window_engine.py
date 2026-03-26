from src.domain_models.exceptions import InvalidScheduleError
from src.domain_models.ids import ScheduleId
from src.domain_models.schedule import Schedule
from src.domain_models.task import Task


def build_schedule(schedule_id: ScheduleId, task: Task, due_at: int, reminder_at: int) -> Schedule:
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
