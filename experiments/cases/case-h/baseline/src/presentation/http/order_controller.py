from fastapi import APIRouter, HTTPException

from src.application.use_cases.create_order import CreateOrderUseCase
from src.application.use_cases.fulfill_order import FulfillOrderUseCase
from src.application.use_cases.list_attempts import ListAttemptsUseCase
from src.application.use_cases.list_orders import ListOrdersUseCase
from src.application.use_cases.reconcile_order import ReconcileOrderUseCase
from src.application.use_cases.retry_fulfillment import RetryFulfillmentUseCase
from src.domain.errors import DuplicateFulfillmentAttemptError, OrderNotFoundError
from src.domain.services.fulfillment_policies import new_identifier
from src.presentation.http.order_schemas import (
    AttemptResponseSchema,
    CreateOrderRequestSchema,
    FulfillmentRequestSchema,
    FulfillmentResponseSchema,
    OrderResponseSchema,
    ReconciliationResponseSchema,
    RetryFulfillmentRequestSchema,
)

router = APIRouter()

_create_order_use_case: CreateOrderUseCase | None = None
_list_orders_use_case: ListOrdersUseCase | None = None
_fulfill_order_use_case: FulfillOrderUseCase | None = None
_retry_fulfillment_use_case: RetryFulfillmentUseCase | None = None
_reconcile_order_use_case: ReconcileOrderUseCase | None = None
_list_attempts_use_case: ListAttemptsUseCase | None = None


def wire_use_cases(
    *,
    create_order_use_case: CreateOrderUseCase,
    list_orders_use_case: ListOrdersUseCase,
    fulfill_order_use_case: FulfillOrderUseCase,
    retry_fulfillment_use_case: RetryFulfillmentUseCase,
    reconcile_order_use_case: ReconcileOrderUseCase,
    list_attempts_use_case: ListAttemptsUseCase,
) -> None:
    global _create_order_use_case, _list_orders_use_case, _fulfill_order_use_case
    global _retry_fulfillment_use_case, _reconcile_order_use_case, _list_attempts_use_case
    _create_order_use_case = create_order_use_case
    _list_orders_use_case = list_orders_use_case
    _fulfill_order_use_case = fulfill_order_use_case
    _retry_fulfillment_use_case = retry_fulfillment_use_case
    _reconcile_order_use_case = reconcile_order_use_case
    _list_attempts_use_case = list_attempts_use_case


def _require_use_cases() -> tuple[
    CreateOrderUseCase,
    ListOrdersUseCase,
    FulfillOrderUseCase,
    RetryFulfillmentUseCase,
    ReconcileOrderUseCase,
    ListAttemptsUseCase,
]:
    if None in (
        _create_order_use_case,
        _list_orders_use_case,
        _fulfill_order_use_case,
        _retry_fulfillment_use_case,
        _reconcile_order_use_case,
        _list_attempts_use_case,
    ):
        raise RuntimeError("Use cases are not wired.")
    return (
        _create_order_use_case,
        _list_orders_use_case,
        _fulfill_order_use_case,
        _retry_fulfillment_use_case,
        _reconcile_order_use_case,
        _list_attempts_use_case,
    )


@router.post("/orders", response_model=OrderResponseSchema)
def create_order(request: CreateOrderRequestSchema) -> OrderResponseSchema:
    create_order_use_case, _, _, _, _, _ = _require_use_cases()
    order = create_order_use_case.execute(request.to_domain(new_identifier("order")))
    return OrderResponseSchema.from_domain(order)


@router.get("/orders", response_model=list[OrderResponseSchema])
def list_orders() -> list[OrderResponseSchema]:
    _, list_orders_use_case, _, _, _, _ = _require_use_cases()
    return [OrderResponseSchema.from_domain(order) for order in list_orders_use_case.execute()]


@router.post("/orders/{order_id}/fulfill", response_model=FulfillmentResponseSchema)
def fulfill_order(order_id: str, request: FulfillmentRequestSchema) -> FulfillmentResponseSchema:
    _, _, fulfill_order_use_case, _, _, _ = _require_use_cases()
    try:
        order, attempt, authorization, shipment = fulfill_order_use_case.execute(order_id, request.idempotency_key)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FulfillmentResponseSchema(
        order=OrderResponseSchema.from_domain(order),
        attempt_id=attempt.id,
        attempt_status=attempt.status,
        error_code=attempt.error_code,
        authorization_status=authorization.status if authorization else None,
        shipment_id=shipment.id if shipment else None,
        tracking_code=shipment.tracking_code if shipment else None,
    )


@router.post("/orders/{order_id}/retry", response_model=FulfillmentResponseSchema)
def retry_fulfillment(order_id: str, request: RetryFulfillmentRequestSchema) -> FulfillmentResponseSchema:
    _, _, _, retry_fulfillment_use_case, _, _ = _require_use_cases()
    try:
        order, attempt, authorization, shipment = retry_fulfillment_use_case.execute(order_id, request.idempotency_key)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DuplicateFulfillmentAttemptError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return FulfillmentResponseSchema(
        order=OrderResponseSchema.from_domain(order),
        attempt_id=attempt.id,
        attempt_status=attempt.status,
        error_code=attempt.error_code,
        authorization_status=authorization.status if authorization else None,
        shipment_id=shipment.id if shipment else None,
        tracking_code=shipment.tracking_code if shipment else None,
    )


@router.post("/orders/{order_id}/reconcile", response_model=ReconciliationResponseSchema)
def reconcile_order(order_id: str) -> ReconciliationResponseSchema:
    _, _, _, _, reconcile_order_use_case, _ = _require_use_cases()
    try:
        order_id, resolved_status, reason, attempt_count, authorization_count, shipment_count = reconcile_order_use_case.execute(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ReconciliationResponseSchema(
        order_id=order_id,
        resolved_status=resolved_status,
        reason=reason,
        attempt_count=attempt_count,
        authorization_count=authorization_count,
        shipment_count=shipment_count,
    )


@router.get("/orders/{order_id}/attempts", response_model=list[AttemptResponseSchema])
def list_attempts(order_id: str) -> list[AttemptResponseSchema]:
    _, _, _, _, _, list_attempts_use_case = _require_use_cases()
    try:
        attempts = list_attempts_use_case.execute(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [
        AttemptResponseSchema(
            id=attempt.id,
            idempotency_key=attempt.idempotency_key,
            status=attempt.status,
            step=attempt.step,
            error_code=attempt.error_code,
        )
        for attempt in attempts
    ]
