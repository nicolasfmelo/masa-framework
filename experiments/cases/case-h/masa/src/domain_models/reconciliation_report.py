from dataclasses import dataclass

from src.domain_models.order import OrderStatus


@dataclass(frozen=True)
class ReconciliationReport:
    order_id: str
    resolved_status: OrderStatus
    reason: str | None
    attempt_count: int
    authorization_count: int
    shipment_count: int
