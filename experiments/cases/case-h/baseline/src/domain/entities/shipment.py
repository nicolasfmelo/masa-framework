from dataclasses import dataclass

VALID_SHIPMENT_STATUSES = {"queued", "scheduled", "cancelled"}


@dataclass(frozen=True)
class Shipment:
    id: str
    order_id: str
    warehouse_id: str
    carrier: str
    tracking_code: str
    status: str

    def __post_init__(self) -> None:
        if self.status not in VALID_SHIPMENT_STATUSES:
            raise ValueError(f"Invalid shipment status: {self.status}")
