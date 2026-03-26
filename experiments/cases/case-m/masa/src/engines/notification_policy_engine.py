from src.domain_models.exceptions import NotificationPolicyConflictError
from src.domain_models.notification_policy import NotificationPolicy
from src.domain_models.schedule import Schedule


def validate_notification_policy(policy: NotificationPolicy, schedule: Schedule) -> None:
    minutes_until_due = (schedule.due_at - schedule.reminder_at) // 60
    if policy.remind_before_minutes <= 0:
        raise NotificationPolicyConflictError("remind_before_minutes must be positive.")
    if policy.remind_before_minutes > minutes_until_due:
        raise NotificationPolicyConflictError(
            "Notification policy requests a reminder earlier than the schedule allows."
        )
