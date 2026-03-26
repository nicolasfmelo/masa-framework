from src.domain_models.inventory import Anomaly, InventoryReport, StockItem, StockMovement

LOW_STOCK_THRESHOLD = 10


def calculate_inventory(movements: list[StockMovement]) -> InventoryReport:
    """
    Pure function. Processes a list of movements sorted by timestamp and
    returns the final inventory state with low-stock alerts and anomalies.
    """
    sorted_movements = sorted(movements, key=lambda m: m.timestamp)

    quantities: dict[str, int] = {}
    names: dict[str, str] = {}
    anomalous_ids: set[str] = set()

    for movement in sorted_movements:
        pid = movement.product_id
        names[pid] = movement.product_name

        if pid not in quantities:
            quantities[pid] = 0

        if movement.movement_type == "in":
            quantities[pid] += movement.quantity
        else:
            quantities[pid] -= movement.quantity
            if quantities[pid] < 0:
                anomalous_ids.add(pid)

    stock = [
        StockItem(product_id=pid, product_name=names[pid], quantity=qty)
        for pid, qty in quantities.items()
    ]

    low_stock = [item for item in stock if item.quantity < LOW_STOCK_THRESHOLD]

    anomalies = [
        Anomaly(
            product_id=pid,
            product_name=names[pid],
            message="Stock went negative",
        )
        for pid in anomalous_ids
    ]

    return InventoryReport(stock=stock, low_stock=low_stock, anomalies=anomalies)
