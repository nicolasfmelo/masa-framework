from dataclasses import dataclass
from typing import Literal

from src.domain_models.ids import OrderId, ShipmentId, WarehouseId

ShipmentStatus = Literal["queued", "scheduled", "cancelled"]


@dataclass(frozen=True)
class Shipment:
    id: ShipmentId
    order_id: OrderId
    warehouse_id: WarehouseId
    carrier: str
    tracking_code: str
    status: ShipmentStatus
