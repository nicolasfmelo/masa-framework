import csv
import io

from src.domain_models.exceptions import InvalidCSVError, InvalidRowError
from src.domain_models.inventory import StockMovement

REQUIRED_COLUMNS = {"timestamp", "product_id", "product_name", "type", "quantity"}


def parse_csv(file_content: str) -> list[StockMovement]:
    """
    Parses CSV text into a list of StockMovement domain models.
    Skips malformed rows without crashing. Raises InvalidCSVError if
    the file structure is completely unparsable.
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except Exception as exc:
        raise InvalidCSVError("Could not read the uploaded file as CSV.") from exc

    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise InvalidCSVError(
            f"CSV is missing required columns. Expected: {REQUIRED_COLUMNS}"
        )

    movements: list[StockMovement] = []

    for row in reader:
        try:
            movements.append(_parse_row(row))
        except InvalidRowError:
            continue

    return movements


def _parse_row(row: dict) -> StockMovement:
    try:
        timestamp = int(row["timestamp"])
        product_id = row["product_id"].strip()
        product_name = row["product_name"].strip()
        movement_type = row["type"].strip().lower()
        quantity = int(row["quantity"])

        if not product_id or not product_name:
            raise ValueError("product_id and product_name must not be empty.")
        if movement_type not in ("in", "out"):
            raise ValueError(f"Invalid movement type: '{movement_type}'.")
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        return StockMovement(
            timestamp=timestamp,
            product_id=product_id,
            product_name=product_name,
            movement_type=movement_type,
            quantity=quantity,
        )
    except (KeyError, ValueError, AttributeError) as exc:
        raise InvalidRowError(f"Skipping malformed row: {row}. Reason: {exc}") from exc
