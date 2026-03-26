from dataclasses import replace

from src.domain_models.ids import OrderId
from src.domain_models.reconciliation_report import ReconciliationReport
from src.engines.reconciliation_engine import derive_reconciliation_status
from src.integrations.database.repos.fulfillment_attempt_repo import FulfillmentAttemptRepository
from src.integrations.database.repos.order_repo import OrderRepository
from src.integrations.database.repos.payment_authorization_repo import PaymentAuthorizationRepository
from src.integrations.database.repos.shipment_repo import ShipmentRepository


class ReconciliationService:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentAuthorizationRepository,
        shipment_repo: ShipmentRepository,
        attempt_repo: FulfillmentAttemptRepository,
    ):
        self._order_repo = order_repo
        self._payment_repo = payment_repo
        self._shipment_repo = shipment_repo
        self._attempt_repo = attempt_repo

    def reconcile_order(self, order_id: OrderId) -> ReconciliationReport:
        order = self._order_repo.find_by_id(order_id)
        authorizations = self._payment_repo.list_by_order(order_id)
        shipments = self._shipment_repo.list_by_order(order_id)
        attempts = self._attempt_repo.list_by_order(order_id)
        resolved_status, reason = derive_reconciliation_status(order, attempts, authorizations, shipments)
        updated_order = replace(
            order,
            status=resolved_status,
            failure_reason=reason,
            shipment_id=shipments[-1].id if shipments else order.shipment_id,
        )
        self._order_repo.save(updated_order)
        return ReconciliationReport(
            order_id=order_id.value,
            resolved_status=resolved_status,
            reason=reason,
            attempt_count=len(attempts),
            authorization_count=len(authorizations),
            shipment_count=len(shipments),
        )
