from src.application.ports import FulfillmentAttemptRepository, OrderRepository
from src.domain.entities.fulfillment_attempt import FulfillmentAttempt


class ListAttemptsUseCase:
    def __init__(self, order_repository: OrderRepository, attempt_repository: FulfillmentAttemptRepository):
        self._order_repository = order_repository
        self._attempt_repository = attempt_repository

    def execute(self, order_id: str) -> list[FulfillmentAttempt]:
        self._order_repository.find_by_id(order_id)
        return self._attempt_repository.list_by_order(order_id)
