from src.domain_models.fulfillment_attempt import FulfillmentAttempt
from src.domain_models.ids import OrderId


class FulfillmentAttemptRepository:
    def __init__(self, storage: dict[str, FulfillmentAttempt], idempotency_index: dict[tuple[str, str], str]):
        self._storage = storage
        self._idempotency_index = idempotency_index

    def save(self, attempt: FulfillmentAttempt) -> FulfillmentAttempt:
        self._storage[attempt.id.value] = attempt
        self._idempotency_index[(attempt.order_id.value, attempt.idempotency_key)] = attempt.id.value
        return attempt

    def find_by_idempotency_key(self, order_id: OrderId, idempotency_key: str) -> FulfillmentAttempt | None:
        attempt_id = self._idempotency_index.get((order_id.value, idempotency_key))
        if attempt_id is None:
            return None
        return self._storage[attempt_id]

    def list_by_order(self, order_id: OrderId) -> list[FulfillmentAttempt]:
        return [item for item in self._storage.values() if item.order_id.value == order_id.value]
