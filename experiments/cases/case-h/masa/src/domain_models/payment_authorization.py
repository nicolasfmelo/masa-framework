from dataclasses import dataclass
from typing import Literal

from src.domain_models.ids import OrderId, PaymentAuthorizationId

PaymentAuthorizationStatus = Literal["authorized", "declined"]
PaymentRiskBand = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class PaymentAuthorization:
    id: PaymentAuthorizationId
    order_id: OrderId
    amount_cents: int
    risk_band: PaymentRiskBand
    status: PaymentAuthorizationStatus
    gateway_reference: str
