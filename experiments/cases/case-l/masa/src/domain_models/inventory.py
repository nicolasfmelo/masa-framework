from dataclasses import dataclass, field
from typing import Literal


@dataclass
class StockMovement:
    timestamp: int
    product_id: str
    product_name: str
    movement_type: Literal["in", "out"]
    quantity: int


@dataclass
class StockItem:
    product_id: str
    product_name: str
    quantity: int


@dataclass
class Anomaly:
    product_id: str
    product_name: str
    message: str


@dataclass
class InventoryReport:
    stock: list[StockItem] = field(default_factory=list)
    low_stock: list[StockItem] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
