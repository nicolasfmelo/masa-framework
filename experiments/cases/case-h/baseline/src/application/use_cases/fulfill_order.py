from dataclasses import replace

from src.application.ports import (
    FulfillmentAttemptRepository,
    InventoryRepository,
    OrderRepository,
    PaymentAuthorizationRepository,
    PaymentGateway,
    ShipmentGateway,
    ShipmentRepository,
    WarehouseEventPublisher,
)
from src.domain.entities.fulfillment_attempt import FulfillmentAttempt
from src.domain.entities.order import Order
from src.domain.entities.payment_authorization import PaymentAuthorization
from src.domain.entities.shipment import Shipment
from src.domain.errors import (
    DuplicateFulfillmentAttemptError,
    InventoryUnavailableError,
    PaymentDeclinedError,
    ShipmentPlanningError,
)
from src.domain.services.fulfillment_policies import (
    assess_payment_risk,
    new_identifier,
    plan_allocations,
    plan_shipment,
)


class FulfillOrderUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        inventory_repository: InventoryRepository,
        payment_repository: PaymentAuthorizationRepository,
        shipment_repository: ShipmentRepository,
        attempt_repository: FulfillmentAttemptRepository,
        payment_gateway: PaymentGateway,
        shipment_gateway: ShipmentGateway,
        event_publisher: WarehouseEventPublisher,
    ):
        self._order_repository = order_repository
        self._inventory_repository = inventory_repository
        self._payment_repository = payment_repository
        self._shipment_repository = shipment_repository
        self._attempt_repository = attempt_repository
        self._payment_gateway = payment_gateway
        self._shipment_gateway = shipment_gateway
        self._event_publisher = event_publisher

    def execute(self, order_id: str, idempotency_key: str) -> tuple[Order, FulfillmentAttempt, PaymentAuthorization | None, Shipment | None]:
        order = self._order_repository.find_by_id(order_id)
        existing_attempt = self._attempt_repository.find_by_idempotency_key(order_id, idempotency_key)
        if existing_attempt is not None:
            return self._snapshot(order, existing_attempt)

        started_attempt = FulfillmentAttempt(
            id=new_identifier("attempt"),
            order_id=order.id,
            idempotency_key=idempotency_key,
            status="in_progress",
            step="inventory_allocation",
            error_code=None,
        )
        self._attempt_repository.save(started_attempt)
        in_progress_order = replace(order, status="fulfillment_in_progress", last_attempt_id=started_attempt.id, failure_reason=None)
        self._order_repository.save(in_progress_order)
        self._event_publisher.publish("fulfillment_started", {"order_id": order.id, "idempotency_key": idempotency_key})

        try:
            stocks = self._inventory_repository.list_by_skus({line.sku for line in in_progress_order.line_items})
            allocations = plan_allocations(in_progress_order, stocks)
            self._inventory_repository.reserve_allocations(allocations)
            risk_band = assess_payment_risk(in_progress_order)
            authorization = self._payment_gateway.authorize_payment(in_progress_order, risk_band)
            self._payment_repository.save(authorization)
            if authorization.status == "declined":
                raise PaymentDeclinedError("Payment authorization was declined.")
            warehouse_id, carrier = plan_shipment(in_progress_order, allocations, risk_band)
            shipment = self._shipment_gateway.create_shipment(in_progress_order, warehouse_id, carrier)
            self._shipment_repository.save(shipment)
            completed_attempt = replace(started_attempt, status="succeeded", step="completed")
            self._attempt_repository.save(completed_attempt)
            fulfilled_order = replace(
                in_progress_order,
                status="fulfilled",
                shipment_id=shipment.id,
                last_attempt_id=completed_attempt.id,
                failure_reason=None,
            )
            self._order_repository.save(fulfilled_order)
            self._event_publisher.publish(
                "fulfillment_succeeded",
                {"order_id": fulfilled_order.id, "shipment_id": shipment.id, "carrier": shipment.carrier},
            )
            return fulfilled_order, completed_attempt, authorization, shipment
        except (InventoryUnavailableError, PaymentDeclinedError, ShipmentPlanningError) as exc:
            failed_attempt = replace(started_attempt, status="failed", step="failed", error_code=type(exc).__name__)
            self._attempt_repository.save(failed_attempt)
            failed_order = replace(in_progress_order, status="failed", last_attempt_id=failed_attempt.id, failure_reason=str(exc))
            self._order_repository.save(failed_order)
            self._event_publisher.publish(
                "fulfillment_failed",
                {"order_id": failed_order.id, "error_code": type(exc).__name__},
            )
            return self._snapshot(failed_order, failed_attempt)

    def _snapshot(self, order: Order, attempt: FulfillmentAttempt) -> tuple[Order, FulfillmentAttempt, PaymentAuthorization | None, Shipment | None]:
        authorizations = self._payment_repository.list_by_order(order.id)
        shipments = self._shipment_repository.list_by_order(order.id)
        return order, attempt, (authorizations[-1] if authorizations else None), (shipments[-1] if shipments else None)
