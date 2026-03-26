from src.domain_models.assignee import Assignee
from src.domain_models.exceptions import AssigneeNotFoundError
from src.domain_models.ids import AssigneeId


class AssigneeRepository:
    def __init__(self, storage: dict[str, Assignee]):
        self._storage = storage

    def save(self, assignee: Assignee) -> Assignee:
        self._storage[assignee.id.value] = assignee
        return assignee

    def find_by_id(self, assignee_id: AssigneeId) -> Assignee:
        assignee = self._storage.get(assignee_id.value)
        if assignee is None:
            raise AssigneeNotFoundError(f"Assignee {assignee_id.value} not found.")
        return assignee
