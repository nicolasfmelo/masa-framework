from dataclasses import dataclass

VALID_ORDER_STATUSES = {
    "draft",
    "accepted",
    "fulfillment_in_progress",
    "fulfilled",
    "failed",
    "reconciliation_required",
}


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    region: str
    currency: str
    payment_token: str
    line_items: tuple[OrderLine, ...]
    status: str
    total_amount_cents: int
    shipment_id: str | None
    last_attempt_id: str | None
    failure_reason: str | None

    def __post_init__(self) -> None:
        if self.status not in VALID_ORDER_STATUSES:
            raise ValueError(f"Invalid order status: {self.status}")
