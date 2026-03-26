import csv
import io

# R4: raises ValueError and csv.Error directly — no domain exception wrapping.
# R1: returns list[dict] with raw string keys, not domain objects.

REQUIRED_COLUMNS = {"timestamp", "product_id", "product_name", "type", "quantity"}


def parse_csv(file_content: str) -> list[dict]:
    """Parse CSV text into a list of raw row dicts."""
    reader = csv.DictReader(io.StringIO(file_content))

    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise ValueError(
            f"CSV is missing required columns. Expected: {REQUIRED_COLUMNS}"
        )

    rows = []
    for row in reader:
        product_id = row["product_id"].strip()
        product_name = row["product_name"].strip()
        movement_type = row["type"].strip().lower()
        quantity = int(row["quantity"])
        timestamp = int(row["timestamp"])

        if not product_id or not product_name:
            raise ValueError("product_id and product_name must not be empty.")
        if movement_type not in ("in", "out"):
            raise ValueError(f"Invalid movement type: '{movement_type}'.")
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        rows.append({
            "timestamp": timestamp,
            "product_id": product_id,
            "product_name": product_name,
            "type": movement_type,
            "quantity": quantity,
        })

    return rows
