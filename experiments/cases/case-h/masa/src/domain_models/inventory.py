from dataclasses import dataclass

from src.domain_models.ids import WarehouseId


@dataclass(frozen=True)
class WarehouseStock:
    warehouse_id: WarehouseId
    sku: str
    region: str
    available_units: int


@dataclass(frozen=True)
class InventoryAllocation:
    warehouse_id: WarehouseId
    sku: str
    quantity: int
