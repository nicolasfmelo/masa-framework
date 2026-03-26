from collections import defaultdict

from src.domain_models.exceptions import InventoryUnavailableError
from src.domain_models.inventory import InventoryAllocation, WarehouseStock
from src.domain_models.order import Order


def plan_inventory_allocations(order: Order, stocks: list[WarehouseStock]) -> list[InventoryAllocation]:
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
            key=lambda item: (item.region != order.region, -item.available_units, item.warehouse_id.value),
        )
        remaining = needed
        for candidate in candidates:
            if remaining <= 0:
                break
            reserved = min(candidate.available_units, remaining)
            if reserved <= 0:
                continue
            allocations.append(
                InventoryAllocation(
                    warehouse_id=candidate.warehouse_id,
                    sku=sku,
                    quantity=reserved,
                )
            )
            remaining -= reserved

        if remaining > 0:
            raise InventoryUnavailableError(f"Insufficient inventory for {sku}.")

    return allocations
