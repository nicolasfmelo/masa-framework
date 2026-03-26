class TaskNotFoundError(Exception):
    pass


class AssigneeNotFoundError(Exception):
    pass


class InvalidScheduleError(Exception):
    pass


class NotificationPolicyConflictError(Exception):
    pass
