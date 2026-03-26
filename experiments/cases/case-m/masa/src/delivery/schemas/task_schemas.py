from pydantic import BaseModel


class NotificationPolicySchema(BaseModel):
    channel: str
    remind_before_minutes: int
    send_on_assignment: bool


class CreateTaskRequestSchema(BaseModel):
    id: str
    title: str
    description: str
    estimated_minutes: int
    notification_policy: NotificationPolicySchema


class UpdateTaskRequestSchema(BaseModel):
    title: str
    description: str
    status: str
    estimated_minutes: int


class AssignTaskRequestSchema(BaseModel):
    assignee_id: str


class ScheduleTaskRequestSchema(BaseModel):
    schedule_id: str
    due_at: int
    reminder_at: int


class TaskResponseSchema(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    assignee_id: str | None
    estimated_minutes: int
    notification_channel: str
    remind_before_minutes: int
    send_on_assignment: bool


class ScheduleResponseSchema(BaseModel):
    id: str
    task_id: str
    due_at: int
    reminder_at: int
