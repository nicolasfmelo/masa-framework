from dataclasses import dataclass


@dataclass(frozen=True)
class WarehouseStock:
    warehouse_id: str
    sku: str
    region: str
    available_units: int


@dataclass(frozen=True)
class InventoryAllocation:
    warehouse_id: str
    sku: str
    quantity: int
