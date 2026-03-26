from src.domain_models.fulfillment_attempt import FulfillmentAttempt
from src.domain_models.order import Order, OrderStatus
from src.domain_models.payment_authorization import PaymentAuthorization
from src.domain_models.shipment import Shipment


def derive_reconciliation_status(
    order: Order,
    attempts: list[FulfillmentAttempt],
    authorizations: list[PaymentAuthorization],
    shipments: list[Shipment],
) -> tuple[OrderStatus, str | None]:
    has_authorized_payment = any(item.status == "authorized" for item in authorizations)
    if shipments and has_authorized_payment:
        return "fulfilled", None
    if has_authorized_payment and not shipments:
        return "reconciliation_required", "authorized_payment_without_shipment"
    if attempts and attempts[-1].status == "failed":
        return "reconciliation_required", attempts[-1].error_code or "failed_attempt_requires_review"
    return order.status, order.failure_reason
