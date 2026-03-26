from dataclasses import dataclass


@dataclass(frozen=True)
class Assignee:
    id: str
    name: str
    email: str
    timezone: str
