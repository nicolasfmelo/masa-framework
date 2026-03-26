from src.domain_models.exceptions import ShipmentPlanningError
from src.domain_models.ids import ShipmentId, WarehouseId
from src.domain_models.order import Order
from src.domain_models.shipment import Shipment


class ShipmentGateway:
    def create_shipment(self, order: Order, warehouse_id: WarehouseId, carrier: str) -> Shipment:
        if order.region == "blocked-region":
            raise ShipmentPlanningError("Shipment carrier unavailable for region.")
        return Shipment(
            id=ShipmentId.new(),
            order_id=order.id,
            warehouse_id=warehouse_id,
            carrier=carrier,
            tracking_code=f"trk-{order.id.value[-6:]}-{warehouse_id.value[-3:]}",
            status="queued",
        )
