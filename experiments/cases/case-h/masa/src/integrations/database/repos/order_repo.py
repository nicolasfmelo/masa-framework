from src.domain_models.exceptions import OrderNotFoundError
from src.domain_models.ids import OrderId
from src.domain_models.order import Order


class OrderRepository:
    def __init__(self, storage: dict[str, Order]):
        self._storage = storage

    def save(self, order: Order) -> Order:
        self._storage[order.id.value] = order
        return order

    def find_by_id(self, order_id: OrderId) -> Order:
        try:
            return self._storage[order_id.value]
        except KeyError as exc:
            raise OrderNotFoundError(f"Order {order_id.value} not found.") from exc

    def list_all(self) -> list[Order]:
        return list(self._storage.values())
