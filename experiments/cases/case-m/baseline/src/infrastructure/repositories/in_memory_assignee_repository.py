from src.domain.entities.assignee import Assignee
from src.domain.errors import AssigneeNotFoundError


class InMemoryAssigneeRepository:
    def __init__(self, storage: dict[str, Assignee]):
        self._storage = storage

    def get_by_id(self, assignee_id: str) -> Assignee:
        assignee = self._storage.get(assignee_id)
        if assignee is None:
            raise AssigneeNotFoundError(f"Assignee {assignee_id} not found.")
        return assignee
