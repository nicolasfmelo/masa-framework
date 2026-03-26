from collections import defaultdict
from uuid import uuid4

from src.domain.entities.fulfillment_attempt import FulfillmentAttempt
from src.domain.entities.inventory import InventoryAllocation, WarehouseStock
from src.domain.entities.order import Order
from src.domain.entities.payment_authorization import PaymentAuthorization
from src.domain.entities.shipment import Shipment
from src.domain.errors import InventoryUnavailableError, ShipmentPlanningError


def new_identifier(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def plan_allocations(order: Order, stocks: list[WarehouseStock]) -> list[InventoryAllocation]:
    needed_by_sku: dict[str, int] = defaultdict(int)
    for line in order.line_items:
        needed_by_sku[line.sku] += line.quantity

    grouped: dict[str, list[WarehouseStock]] = defaultdict(list)
    for stock in stocks:
        grouped[stock.sku].append(stock)

    allocations: list[InventoryAllocation] = []
    for sku, needed in needed_by_sku.items():
        candidates = sorted(
            grouped.get(sku, []),
            key=lambda item: (item.region != order.region, -item.available_units, item.warehouse_id),
        )
        remaining = needed
        for candidate in candidates:
            if remaining <= 0:
                break
            reserved = min(candidate.available_units, remaining)
            if reserved <= 0:
                continue
            allocations.append(InventoryAllocation(candidate.warehouse_id, sku, reserved))
            remaining -= reserved
        if remaining > 0:
            raise InventoryUnavailableError(f"Insufficient inventory for {sku}.")
    return allocations


def assess_payment_risk(order: Order) -> str:
    total_units = sum(line.quantity for line in order.line_items)
    if order.total_amount_cents >= 300000 or total_units >= 10:
        return "high"
    if order.total_amount_cents >= 120000 or len(order.line_items) >= 3:
        return "medium"
    return "low"


def plan_shipment(order: Order, allocations: list[InventoryAllocation], risk_band: str) -> tuple[str, str]:
    if not allocations:
        raise ShipmentPlanningError("Cannot create shipment without inventory allocations.")
    quantities_by_warehouse: dict[str, int] = defaultdict(int)
    for allocation in allocations:
        quantities_by_warehouse[allocation.warehouse_id] += allocation.quantity
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
    return warehouse_id, carrier


def derive_reconciliation_status(
    order: Order,
    attempts: list[FulfillmentAttempt],
    authorizations: list[PaymentAuthorization],
    shipments: list[Shipment],
) -> tuple[str, str | None]:
    has_authorized_payment = any(item.status == "authorized" for item in authorizations)
    if shipments and has_authorized_payment:
        return "fulfilled", None
    if has_authorized_payment and not shipments:
        return "reconciliation_required", "authorized_payment_without_shipment"
    if attempts and attempts[-1].status == "failed":
        return "reconciliation_required", attempts[-1].error_code or "failed_attempt_requires_review"
    return order.status, order.failure_reason
