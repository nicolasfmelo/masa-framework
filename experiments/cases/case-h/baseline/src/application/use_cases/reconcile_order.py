from dataclasses import replace

from src.application.ports import (
    FulfillmentAttemptRepository,
    OrderRepository,
    PaymentAuthorizationRepository,
    ShipmentRepository,
)
from src.domain.services.fulfillment_policies import derive_reconciliation_status


class ReconcileOrderUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        payment_repository: PaymentAuthorizationRepository,
        shipment_repository: ShipmentRepository,
        attempt_repository: FulfillmentAttemptRepository,
    ):
        self._order_repository = order_repository
        self._payment_repository = payment_repository
        self._shipment_repository = shipment_repository
        self._attempt_repository = attempt_repository

    def execute(self, order_id: str) -> tuple[str, str, str | None, int, int, int]:
        order = self._order_repository.find_by_id(order_id)
        authorizations = self._payment_repository.list_by_order(order_id)
        shipments = self._shipment_repository.list_by_order(order_id)
        attempts = self._attempt_repository.list_by_order(order_id)
        resolved_status, reason = derive_reconciliation_status(order, attempts, authorizations, shipments)
        updated_order = replace(
            order,
            status=resolved_status,
            failure_reason=reason,
            shipment_id=shipments[-1].id if shipments else order.shipment_id,
        )
        self._order_repository.save(updated_order)
        return order_id, resolved_status, reason, len(attempts), len(authorizations), len(shipments)
