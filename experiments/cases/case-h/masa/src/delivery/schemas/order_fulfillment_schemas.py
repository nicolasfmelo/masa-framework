from pydantic import BaseModel, Field

from src.domain_models.ids import CustomerId, OrderId
from src.domain_models.order import Order, OrderLine


class OrderLineRequestSchema(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(gt=0)

    def to_domain(self) -> OrderLine:
        return OrderLine(
            sku=self.sku,
            quantity=self.quantity,
            unit_price_cents=self.unit_price_cents,
        )


class CreateOrderRequestSchema(BaseModel):
    customer_id: str
    region: str
    currency: str = "USD"
    payment_token: str
    line_items: list[OrderLineRequestSchema]

    def to_domain(self) -> Order:
        lines = tuple(item.to_domain() for item in self.line_items)
        total_amount_cents = sum(item.quantity * item.unit_price_cents for item in lines)
        return Order(
            id=OrderId.new(),
            customer_id=CustomerId(self.customer_id),
            region=self.region,
            currency=self.currency,
            payment_token=self.payment_token,
            line_items=lines,
            status="draft",
            total_amount_cents=total_amount_cents,
            shipment_id=None,
            last_attempt_id=None,
            failure_reason=None,
        )


class FulfillmentRequestSchema(BaseModel):
    idempotency_key: str


class RetryFulfillmentRequestSchema(BaseModel):
    idempotency_key: str


class OrderLineResponseSchema(BaseModel):
    sku: str
    quantity: int
    unit_price_cents: int


class OrderResponseSchema(BaseModel):
    id: str
    customer_id: str
    region: str
    currency: str
    status: str
    total_amount_cents: int
    shipment_id: str | None
    last_attempt_id: str | None
    failure_reason: str | None
    line_items: list[OrderLineResponseSchema]

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponseSchema":
        return cls(
            id=order.id.value,
            customer_id=order.customer_id.value,
            region=order.region,
            currency=order.currency,
            status=order.status,
            total_amount_cents=order.total_amount_cents,
            shipment_id=order.shipment_id.value if order.shipment_id else None,
            last_attempt_id=order.last_attempt_id.value if order.last_attempt_id else None,
            failure_reason=order.failure_reason,
            line_items=[
                OrderLineResponseSchema(
                    sku=line.sku,
                    quantity=line.quantity,
                    unit_price_cents=line.unit_price_cents,
                )
                for line in order.line_items
            ],
        )


class FulfillmentResponseSchema(BaseModel):
    order: OrderResponseSchema
    attempt_id: str
    attempt_status: str
    error_code: str | None
    authorization_status: str | None
    shipment_id: str | None
    tracking_code: str | None


class AttemptResponseSchema(BaseModel):
    id: str
    idempotency_key: str
    status: str
    step: str
    error_code: str | None


class ReconciliationResponseSchema(BaseModel):
    order_id: str
    resolved_status: str
    reason: str | None
    attempt_count: int
    authorization_count: int
    shipment_count: int
