from typing import Protocol

from src.domain.entities.assignee import Assignee


class AssigneeRepository(Protocol):
    def get_by_id(self, assignee_id: str) -> Assignee: ...
