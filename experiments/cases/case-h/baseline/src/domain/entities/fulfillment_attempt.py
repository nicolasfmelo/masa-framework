from dataclasses import dataclass

VALID_ATTEMPT_STATUSES = {"in_progress", "succeeded", "failed"}


@dataclass(frozen=True)
class FulfillmentAttempt:
    id: str
    order_id: str
    idempotency_key: str
    status: str
    step: str
    error_code: str | None

    def __post_init__(self) -> None:
        if self.status not in VALID_ATTEMPT_STATUSES:
            raise ValueError(f"Invalid attempt status: {self.status}")
