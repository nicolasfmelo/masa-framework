from dataclasses import replace

from src.application.ports import FulfillmentAttemptRepository, OrderRepository
from src.application.use_cases.fulfill_order import FulfillOrderUseCase
from src.domain.errors import DuplicateFulfillmentAttemptError


class RetryFulfillmentUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        fulfill_order_use_case: FulfillOrderUseCase,
        attempt_repository: FulfillmentAttemptRepository,
    ):
        self._order_repository = order_repository
        self._fulfill_order_use_case = fulfill_order_use_case
        self._attempt_repository = attempt_repository

    def execute(self, order_id: str, idempotency_key: str):
        order = self._order_repository.find_by_id(order_id)
        attempts = self._attempt_repository.list_by_order(order_id)
        if attempts and attempts[-1].status != "failed":
            raise DuplicateFulfillmentAttemptError("Only failed orders can be retried.")
        reset_order = replace(order, status="accepted", failure_reason=None)
        self._order_repository.save(reset_order)
        return self._fulfill_order_use_case.execute(order_id, idempotency_key)
