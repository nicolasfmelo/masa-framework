from dataclasses import dataclass


@dataclass(frozen=True)
class TaskId:
    value: str


@dataclass(frozen=True)
class AssigneeId:
    value: str


@dataclass(frozen=True)
class ScheduleId:
    value: str
