from dataclasses import replace

from src.domain_models.exceptions import InventoryUnavailableError
from src.domain_models.inventory import InventoryAllocation, WarehouseStock


class InventoryRepository:
    def __init__(self, storage: dict[tuple[str, str], WarehouseStock]):
        self._storage = storage

    def list_by_skus(self, skus: set[str]) -> list[WarehouseStock]:
        return [stock for (_, sku), stock in self._storage.items() if sku in skus]

    def reserve_allocations(self, allocations: list[InventoryAllocation]) -> None:
        for allocation in allocations:
            key = (allocation.warehouse_id.value, allocation.sku)
            stock = self._storage.get(key)
            if stock is None or stock.available_units < allocation.quantity:
                raise InventoryUnavailableError(
                    f"Inventory no longer available for {allocation.sku} in {allocation.warehouse_id.value}."
                )
            self._storage[key] = replace(stock, available_units=stock.available_units - allocation.quantity)
