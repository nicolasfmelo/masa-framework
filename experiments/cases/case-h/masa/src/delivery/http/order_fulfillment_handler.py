from fastapi import APIRouter, HTTPException

from src.delivery.schemas.order_fulfillment_schemas import (
    AttemptResponseSchema,
    CreateOrderRequestSchema,
    FulfillmentRequestSchema,
    FulfillmentResponseSchema,
    OrderResponseSchema,
    ReconciliationResponseSchema,
    RetryFulfillmentRequestSchema,
)
from src.domain_models.exceptions import DuplicateFulfillmentAttemptError, OrderNotFoundError
from src.domain_models.ids import OrderId
from src.services.fulfillment_service import FulfillmentService
from src.services.order_intake_service import OrderIntakeService
from src.services.reconciliation_service import ReconciliationService

router = APIRouter()

_order_intake_service: OrderIntakeService | None = None
_fulfillment_service: FulfillmentService | None = None
_reconciliation_service: ReconciliationService | None = None


def wire_services(
    *,
    order_intake_service: OrderIntakeService,
    fulfillment_service: FulfillmentService,
    reconciliation_service: ReconciliationService,
) -> None:
    global _order_intake_service, _fulfillment_service, _reconciliation_service
    _order_intake_service = order_intake_service
    _fulfillment_service = fulfillment_service
    _reconciliation_service = reconciliation_service


def _require_services() -> tuple[OrderIntakeService, FulfillmentService, ReconciliationService]:
    if None in (_order_intake_service, _fulfillment_service, _reconciliation_service):
        raise RuntimeError("Services are not wired.")
    return _order_intake_service, _fulfillment_service, _reconciliation_service


@router.post("/orders", response_model=OrderResponseSchema)
def create_order(request: CreateOrderRequestSchema) -> OrderResponseSchema:
    order_intake_service, _, _ = _require_services()
    order = order_intake_service.create_order(request.to_domain())
    return OrderResponseSchema.from_domain(order)


@router.get("/orders", response_model=list[OrderResponseSchema])
def list_orders() -> list[OrderResponseSchema]:
    order_intake_service, _, _ = _require_services()
    return [OrderResponseSchema.from_domain(order) for order in order_intake_service.list_orders()]


@router.post("/orders/{order_id}/fulfill", response_model=FulfillmentResponseSchema)
def fulfill_order(order_id: str, request: FulfillmentRequestSchema) -> FulfillmentResponseSchema:
    _, fulfillment_service, _ = _require_services()
    try:
        snapshot = fulfillment_service.fulfill_order(OrderId(order_id), request.idempotency_key)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FulfillmentResponseSchema(
        order=OrderResponseSchema.from_domain(snapshot.order),
        attempt_id=snapshot.attempt.id.value,
        attempt_status=snapshot.attempt.status,
        error_code=snapshot.attempt.error_code,
        authorization_status=snapshot.authorization.status if snapshot.authorization else None,
        shipment_id=snapshot.shipment.id.value if snapshot.shipment else None,
        tracking_code=snapshot.shipment.tracking_code if snapshot.shipment else None,
    )


@router.post("/orders/{order_id}/retry", response_model=FulfillmentResponseSchema)
def retry_fulfillment(order_id: str, request: RetryFulfillmentRequestSchema) -> FulfillmentResponseSchema:
    _, fulfillment_service, _ = _require_services()
    try:
        snapshot = fulfillment_service.retry_fulfillment(OrderId(order_id), request.idempotency_key)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DuplicateFulfillmentAttemptError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return FulfillmentResponseSchema(
        order=OrderResponseSchema.from_domain(snapshot.order),
        attempt_id=snapshot.attempt.id.value,
        attempt_status=snapshot.attempt.status,
        error_code=snapshot.attempt.error_code,
        authorization_status=snapshot.authorization.status if snapshot.authorization else None,
        shipment_id=snapshot.shipment.id.value if snapshot.shipment else None,
        tracking_code=snapshot.shipment.tracking_code if snapshot.shipment else None,
    )


@router.post("/orders/{order_id}/reconcile", response_model=ReconciliationResponseSchema)
def reconcile_order(order_id: str) -> ReconciliationResponseSchema:
    _, _, reconciliation_service = _require_services()
    try:
        report = reconciliation_service.reconcile_order(OrderId(order_id))
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ReconciliationResponseSchema(
        order_id=report.order_id,
        resolved_status=report.resolved_status,
        reason=report.reason,
        attempt_count=report.attempt_count,
        authorization_count=report.authorization_count,
        shipment_count=report.shipment_count,
    )


@router.get("/orders/{order_id}/attempts", response_model=list[AttemptResponseSchema])
def list_attempts(order_id: str) -> list[AttemptResponseSchema]:
    _, fulfillment_service, _ = _require_services()
    try:
        attempts = fulfillment_service.list_attempts(OrderId(order_id))
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [
        AttemptResponseSchema(
            id=attempt.id.value,
            idempotency_key=attempt.idempotency_key,
            status=attempt.status,
            step=attempt.step,
            error_code=attempt.error_code,
        )
        for attempt in attempts
    ]
