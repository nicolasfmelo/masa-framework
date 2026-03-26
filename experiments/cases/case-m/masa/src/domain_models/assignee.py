from dataclasses import dataclass

from src.domain_models.ids import AssigneeId


@dataclass(frozen=True)
class Assignee:
    id: AssigneeId
    name: str
    email: str
    timezone: str
