from collections import defaultdict

from src.domain_models.exceptions import ShipmentPlanningError
from src.domain_models.ids import WarehouseId
from src.domain_models.inventory import InventoryAllocation
from src.domain_models.order import Order
from src.domain_models.payment_authorization import PaymentRiskBand


def choose_shipping_plan(
    order: Order,
    allocations: list[InventoryAllocation],
    risk_band: PaymentRiskBand,
) -> tuple[WarehouseId, str]:
    if not allocations:
        raise ShipmentPlanningError("Cannot create shipment without inventory allocations.")

    quantities_by_warehouse: dict[str, int] = defaultdict(int)
    warehouse_by_id: dict[str, WarehouseId] = {}
    for allocation in allocations:
        key = allocation.warehouse_id.value
        quantities_by_warehouse[key] += allocation.quantity
        warehouse_by_id[key] = allocation.warehouse_id

    warehouse_id = max(
        quantities_by_warehouse,
        key=lambda key: (quantities_by_warehouse[key], key.startswith(f"warehouse-{order.region}"), key),
    )
    total_units = sum(item.quantity for item in allocations)
    if total_units >= 8:
        carrier = "freight"
    elif risk_band == "high":
        carrier = "secure-ground"
    else:
        carrier = "express"
    return warehouse_by_id[warehouse_id], carrier
