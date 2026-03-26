from dataclasses import dataclass
from uuid import uuid4


def _new_value(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


@dataclass(frozen=True)
class OrderId:
    value: str

    @classmethod
    def new(cls) -> "OrderId":
        return cls(_new_value("order"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CustomerId:
    value: str

    @classmethod
    def new(cls) -> "CustomerId":
        return cls(_new_value("customer"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class WarehouseId:
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PaymentAuthorizationId:
    value: str

    @classmethod
    def new(cls) -> "PaymentAuthorizationId":
        return cls(_new_value("payment"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ShipmentId:
    value: str

    @classmethod
    def new(cls) -> "ShipmentId":
        return cls(_new_value("shipment"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FulfillmentAttemptId:
    value: str

    @classmethod
    def new(cls) -> "FulfillmentAttemptId":
        return cls(_new_value("attempt"))

    def __str__(self) -> str:
        return self.value
