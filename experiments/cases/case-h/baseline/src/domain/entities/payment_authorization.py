from dataclasses import dataclass

VALID_PAYMENT_STATUSES = {"authorized", "declined"}
VALID_RISK_BANDS = {"low", "medium", "high"}


@dataclass(frozen=True)
class PaymentAuthorization:
    id: str
    order_id: str
    amount_cents: int
    risk_band: str
    status: str
    gateway_reference: str

    def __post_init__(self) -> None:
        if self.status not in VALID_PAYMENT_STATUSES:
            raise ValueError(f"Invalid payment status: {self.status}")
        if self.risk_band not in VALID_RISK_BANDS:
            raise ValueError(f"Invalid risk band: {self.risk_band}")
