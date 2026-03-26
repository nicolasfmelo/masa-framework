from src.domain_models.ids import OrderId
from src.domain_models.shipment import Shipment


class ShipmentRepository:
    def __init__(self, storage: dict[str, Shipment]):
        self._storage = storage

    def save(self, shipment: Shipment) -> Shipment:
        self._storage[shipment.id.value] = shipment
        return shipment

    def list_by_order(self, order_id: OrderId) -> list[Shipment]:
        return [item for item in self._storage.values() if item.order_id.value == order_id.value]
