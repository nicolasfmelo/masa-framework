from dataclasses import dataclass

from src.domain_models.fulfillment_attempt import FulfillmentAttempt
from src.domain_models.order import Order
from src.domain_models.payment_authorization import PaymentAuthorization
from src.domain_models.shipment import Shipment


@dataclass(frozen=True)
class FulfillmentSnapshot:
    order: Order
    attempt: FulfillmentAttempt
    authorization: PaymentAuthorization | None
    shipment: Shipment | None
