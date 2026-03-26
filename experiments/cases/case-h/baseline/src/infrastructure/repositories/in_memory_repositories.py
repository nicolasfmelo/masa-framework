from dataclasses import replace

from src.domain.entities.fulfillment_attempt import FulfillmentAttempt
from src.domain.entities.inventory import InventoryAllocation, WarehouseStock
from src.domain.entities.order import Order
from src.domain.entities.payment_authorization import PaymentAuthorization
from src.domain.entities.shipment import Shipment
from src.domain.errors import InventoryUnavailableError, OrderNotFoundError


class InMemoryOrderRepository:
    def __init__(self, storage: dict[str, Order]):
        self._storage = storage

    def save(self, order: Order) -> Order:
        self._storage[order.id] = order
        return order

    def find_by_id(self, order_id: str) -> Order:
        try:
            return self._storage[order_id]
        except KeyError as exc:
            raise OrderNotFoundError(f"Order {order_id} not found.") from exc

    def list_all(self) -> list[Order]:
        return list(self._storage.values())


class InMemoryInventoryRepository:
    def __init__(self, storage: dict[tuple[str, str], WarehouseStock]):
        self._storage = storage

    def list_by_skus(self, skus: set[str]) -> list[WarehouseStock]:
        return [stock for (_, sku), stock in self._storage.items() if sku in skus]

    def reserve_allocations(self, allocations: list[InventoryAllocation]) -> None:
        for allocation in allocations:
            key = (allocation.warehouse_id, allocation.sku)
            stock = self._storage.get(key)
            if stock is None or stock.available_units < allocation.quantity:
                raise InventoryUnavailableError(
                    f"Inventory no longer available for {allocation.sku} in {allocation.warehouse_id}."
                )
            self._storage[key] = replace(stock, available_units=stock.available_units - allocation.quantity)


class InMemoryPaymentAuthorizationRepository:
    def __init__(self, storage: dict[str, PaymentAuthorization]):
        self._storage = storage

    def save(self, authorization: PaymentAuthorization) -> PaymentAuthorization:
        self._storage[authorization.id] = authorization
        return authorization

    def list_by_order(self, order_id: str) -> list[PaymentAuthorization]:
        return [item for item in self._storage.values() if item.order_id == order_id]


class InMemoryShipmentRepository:
    def __init__(self, storage: dict[str, Shipment]):
        self._storage = storage

    def save(self, shipment: Shipment) -> Shipment:
        self._storage[shipment.id] = shipment
        return shipment

    def list_by_order(self, order_id: str) -> list[Shipment]:
        return [item for item in self._storage.values() if item.order_id == order_id]


class InMemoryFulfillmentAttemptRepository:
    def __init__(self, storage: dict[str, FulfillmentAttempt], idempotency_index: dict[tuple[str, str], str]):
        self._storage = storage
        self._idempotency_index = idempotency_index

    def save(self, attempt: FulfillmentAttempt) -> FulfillmentAttempt:
        self._storage[attempt.id] = attempt
        self._idempotency_index[(attempt.order_id, attempt.idempotency_key)] = attempt.id
        return attempt

    def find_by_idempotency_key(self, order_id: str, idempotency_key: str) -> FulfillmentAttempt | None:
        attempt_id = self._idempotency_index.get((order_id, idempotency_key))
        if attempt_id is None:
            return None
        return self._storage[attempt_id]

    def list_by_order(self, order_id: str) -> list[FulfillmentAttempt]:
        return [item for item in self._storage.values() if item.order_id == order_id]
