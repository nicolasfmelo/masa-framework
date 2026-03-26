from dataclasses import dataclass
from typing import Literal

from src.domain_models.ids import CustomerId, FulfillmentAttemptId, OrderId, ShipmentId

OrderStatus = Literal[
    "draft",
    "accepted",
    "fulfillment_in_progress",
    "fulfilled",
    "failed",
    "reconciliation_required",
]


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True)
class Order:
    id: OrderId
    customer_id: CustomerId
    region: str
    currency: str
    payment_token: str
    line_items: tuple[OrderLine, ...]
    status: OrderStatus
    total_amount_cents: int
    shipment_id: ShipmentId | None
    last_attempt_id: FulfillmentAttemptId | None
    failure_reason: str | None
