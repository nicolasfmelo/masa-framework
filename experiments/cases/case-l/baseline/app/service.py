from app.models import LOW_STOCK_THRESHOLD, Anomaly, StockItem
from app.utils import parse_csv  # R2: static import, no DI


# R2: module-level dependency — parse_csv is coupled at import time, not injected.
# R1: intermediate data flows as list[dict]; StockItem/Anomaly only built at the end
#     of process_data(), not used as typed boundaries between collaborators.
# S1: generic name process_data() instead of analyze() or calculate_inventory().


def process_data(file_content: str) -> dict:
    """
    Parse CSV and compute inventory state.
    Returns a plain dict suitable for JSON serialisation.
    R4: ValueError from parse_csv (infra error) propagates unmodified to caller.
    """
    rows = parse_csv(file_content)  # raises ValueError on bad input

    rows.sort(key=lambda r: r["timestamp"])

    quantities: dict[str, int] = {}
    names: dict[str, str] = {}
    anomalous_ids: set[str] = set()

    for row in rows:
        pid = row["product_id"]
        names[pid] = row["product_name"]
        if pid not in quantities:
            quantities[pid] = 0

        if row["type"] == "in":
            quantities[pid] += row["quantity"]
        else:
            quantities[pid] -= row["quantity"]
            if quantities[pid] < 0:
                anomalous_ids.add(pid)

    stock = [
        StockItem(product_id=pid, product_name=names[pid], quantity=qty)
        for pid, qty in quantities.items()
    ]
    low_stock = [item for item in stock if item.quantity < LOW_STOCK_THRESHOLD]
    anomalies = [
        Anomaly(product_id=pid, product_name=names[pid], message="Stock went negative")
        for pid in anomalous_ids
    ]

    # R1: collapses domain objects back to dicts before returning
    return {
        "stock": [vars(i) for i in stock],
        "low_stock": [vars(i) for i in low_stock],
        "anomalies": [vars(a) for a in anomalies],
    }
