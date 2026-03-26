from dataclasses import replace

from src.domain_models.exceptions import (
    DuplicateFulfillmentAttemptError,
    InventoryUnavailableError,
    PaymentDeclinedError,
    ShipmentPlanningError,
)
from src.domain_models.fulfillment_attempt import FulfillmentAttempt
from src.domain_models.fulfillment_snapshot import FulfillmentSnapshot
from src.domain_models.ids import FulfillmentAttemptId, OrderId
from src.engines.allocation_engine import plan_inventory_allocations
from src.engines.payment_risk_engine import assess_payment_risk
from src.engines.shipment_engine import choose_shipping_plan
from src.integrations.database.repos.fulfillment_attempt_repo import FulfillmentAttemptRepository
from src.integrations.database.repos.inventory_repo import InventoryRepository
from src.integrations.database.repos.order_repo import OrderRepository
from src.integrations.database.repos.payment_authorization_repo import PaymentAuthorizationRepository
from src.integrations.database.repos.shipment_repo import ShipmentRepository
from src.integrations.external_apis.payment_gateway import PaymentGateway
from src.integrations.external_apis.shipment_gateway import ShipmentGateway
from src.integrations.external_apis.warehouse_event_bus import WarehouseEventBus


class FulfillmentService:
    def __init__(
        self,
        order_repo: OrderRepository,
        inventory_repo: InventoryRepository,
        payment_repo: PaymentAuthorizationRepository,
        shipment_repo: ShipmentRepository,
        attempt_repo: FulfillmentAttemptRepository,
        payment_gateway: PaymentGateway,
        shipment_gateway: ShipmentGateway,
        warehouse_event_bus: WarehouseEventBus,
    ):
        self._order_repo = order_repo
        self._inventory_repo = inventory_repo
        self._payment_repo = payment_repo
        self._shipment_repo = shipment_repo
        self._attempt_repo = attempt_repo
        self._payment_gateway = payment_gateway
        self._shipment_gateway = shipment_gateway
        self._warehouse_event_bus = warehouse_event_bus

    def fulfill_order(self, order_id: OrderId, idempotency_key: str) -> FulfillmentSnapshot:
        order = self._order_repo.find_by_id(order_id)
        existing_attempt = self._attempt_repo.find_by_idempotency_key(order_id, idempotency_key)
        if existing_attempt is not None:
            return self._snapshot(order_id, order, existing_attempt)

        started_attempt = FulfillmentAttempt(
            id=FulfillmentAttemptId.new(),
            order_id=order.id,
            idempotency_key=idempotency_key,
            status="in_progress",
            step="inventory_allocation",
            error_code=None,
        )
        self._attempt_repo.save(started_attempt)
        in_progress_order = replace(
            order,
            status="fulfillment_in_progress",
            last_attempt_id=started_attempt.id,
            failure_reason=None,
        )
        self._order_repo.save(in_progress_order)
        self._warehouse_event_bus.publish(
            "fulfillment_started",
            {"order_id": order.id.value, "idempotency_key": idempotency_key},
        )

        try:
            stocks = self._inventory_repo.list_by_skus({line.sku for line in in_progress_order.line_items})
            allocations = plan_inventory_allocations(in_progress_order, stocks)
            self._inventory_repo.reserve_allocations(allocations)
            risk_band = assess_payment_risk(in_progress_order)
            authorization = self._payment_gateway.authorize_payment(in_progress_order, risk_band)
            self._payment_repo.save(authorization)
            if authorization.status == "declined":
                raise PaymentDeclinedError("Payment authorization was declined.")
            warehouse_id, carrier = choose_shipping_plan(in_progress_order, allocations, risk_band)
            shipment = self._shipment_gateway.create_shipment(in_progress_order, warehouse_id, carrier)
            self._shipment_repo.save(shipment)
            completed_attempt = replace(started_attempt, status="succeeded", step="completed")
            self._attempt_repo.save(completed_attempt)
            fulfilled_order = replace(
                in_progress_order,
                status="fulfilled",
                shipment_id=shipment.id,
                last_attempt_id=completed_attempt.id,
                failure_reason=None,
            )
            self._order_repo.save(fulfilled_order)
            self._warehouse_event_bus.publish(
                "fulfillment_succeeded",
                {
                    "order_id": fulfilled_order.id.value,
                    "shipment_id": shipment.id.value,
                    "carrier": shipment.carrier,
                },
            )
            return FulfillmentSnapshot(
                order=fulfilled_order,
                attempt=completed_attempt,
                authorization=authorization,
                shipment=shipment,
            )
        except (InventoryUnavailableError, PaymentDeclinedError, ShipmentPlanningError) as exc:
            error_name = type(exc).__name__
            failed_attempt = replace(started_attempt, status="failed", step="failed", error_code=error_name)
            self._attempt_repo.save(failed_attempt)
            failed_order = replace(
                in_progress_order,
                status="failed",
                last_attempt_id=failed_attempt.id,
                failure_reason=str(exc),
            )
            self._order_repo.save(failed_order)
            self._warehouse_event_bus.publish(
                "fulfillment_failed",
                {"order_id": failed_order.id.value, "error_code": error_name},
            )
            return self._snapshot(order_id, failed_order, failed_attempt)

    def retry_fulfillment(self, order_id: OrderId, idempotency_key: str) -> FulfillmentSnapshot:
        order = self._order_repo.find_by_id(order_id)
        attempts = self._attempt_repo.list_by_order(order_id)
        if attempts and attempts[-1].status != "failed":
            raise DuplicateFulfillmentAttemptError("Only failed orders can be retried.")
        reset_order = replace(order, status="accepted", failure_reason=None)
        self._order_repo.save(reset_order)
        return self.fulfill_order(order_id, idempotency_key)

    def list_attempts(self, order_id: OrderId) -> list[FulfillmentAttempt]:
        self._order_repo.find_by_id(order_id)
        return self._attempt_repo.list_by_order(order_id)

    def _snapshot(
        self,
        order_id: OrderId,
        order,
        attempt: FulfillmentAttempt,
    ) -> FulfillmentSnapshot:
        authorizations = self._payment_repo.list_by_order(order_id)
        shipments = self._shipment_repo.list_by_order(order_id)
        return FulfillmentSnapshot(
            order=order,
            attempt=attempt,
            authorization=authorizations[-1] if authorizations else None,
            shipment=shipments[-1] if shipments else None,
        )
