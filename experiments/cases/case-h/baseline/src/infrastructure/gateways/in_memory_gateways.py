from src.domain.entities.order import Order
from src.domain.entities.payment_authorization import PaymentAuthorization
from src.domain.entities.shipment import Shipment
from src.domain.errors import ShipmentPlanningError
from src.domain.services.fulfillment_policies import new_identifier


class InMemoryPaymentGateway:
    def authorize_payment(self, order: Order, risk_band: str) -> PaymentAuthorization:
        status = "authorized"
        if "decline" in order.payment_token or (risk_band == "high" and order.region == "fraud-zone"):
            status = "declined"
        return PaymentAuthorization(
            id=new_identifier("payment"),
            order_id=order.id,
            amount_cents=order.total_amount_cents,
            risk_band=risk_band,
            status=status,
            gateway_reference=f"gateway-{order.id[-6:]}-{risk_band}",
        )


class InMemoryShipmentGateway:
    def create_shipment(self, order: Order, warehouse_id: str, carrier: str) -> Shipment:
        if order.region == "blocked-region":
            raise ShipmentPlanningError("Shipment carrier unavailable for region.")
        return Shipment(
            id=new_identifier("shipment"),
            order_id=order.id,
            warehouse_id=warehouse_id,
            carrier=carrier,
            tracking_code=f"trk-{order.id[-6:]}-{warehouse_id[-3:]}",
            status="queued",
        )


class InMemoryWarehouseEventPublisher:
    def __init__(self):
        self._events: list[dict[str, str | int | None]] = []

    def publish(self, event_type: str, payload: dict[str, str | int | None]) -> None:
        event = {"event_type": event_type}
        event.update(payload)
        self._events.append(event)

    def list_events(self) -> list[dict[str, str | int | None]]:
        return list(self._events)
