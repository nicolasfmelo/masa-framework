class TaskNotFoundError(Exception):
    """Raised when a task does not exist."""


class AssigneeNotFoundError(Exception):
    """Raised when an assignee does not exist."""


class InvalidScheduleError(Exception):
    """Raised when a schedule request is invalid."""


class NotificationPolicyConflictError(Exception):
    """Raised when a notification policy conflicts with the current task schedule."""
