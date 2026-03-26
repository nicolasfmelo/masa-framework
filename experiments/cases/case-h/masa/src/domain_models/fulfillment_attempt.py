from dataclasses import dataclass
from typing import Literal

from src.domain_models.ids import FulfillmentAttemptId, OrderId

FulfillmentAttemptStatus = Literal["in_progress", "succeeded", "failed"]


@dataclass(frozen=True)
class FulfillmentAttempt:
    id: FulfillmentAttemptId
    order_id: OrderId
    idempotency_key: str
    status: FulfillmentAttemptStatus
    step: str
    error_code: str | None
