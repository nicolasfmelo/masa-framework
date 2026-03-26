# MASA in Python — Language-Specific Guide

## Project Layout

```
src/
├── domain_models/
│   ├── __init__.py
│   ├── order.py              # Order dataclass
│   ├── ids.py                # OrderId, CustomerId value objects
│   └── exceptions.py         # OrderNotFoundError, StorageUnavailableError, …
├── engines/
│   └── order_calculator.py   # calculate_total(), apply_discount()
├── services/
│   └── order_service.py      # OrderService — orchestration
├── integrations/
│   ├── database/
│   │   ├── models/
│   │   │   └── order_model.py        # SQLAlchemy OrderModel
│   │   └── repos/
│   │       └── order_repo.py         # OrderRepository
│   └── external_apis/
│       └── email_client.py           # EmailClient (wraps SMTP / SendGrid SDK)
└── delivery/
    ├── http/
    │   └── order_handler.py          # FastAPI router
    └── schemas/
        ├── create_order_request.py   # Pydantic BaseModel + .to_domain()
        └── create_order_response.py  # Pydantic BaseModel + .from_domain()
```

---

## Domain Models

Use `@dataclass(frozen=True)` for immutable domain entities, or Pydantic `BaseModel`
when you want validation on creation. Avoid SQLAlchemy in domain models entirely.

```python
# domain_models/ids.py
from dataclasses import dataclass
from uuid import UUID, uuid4

@dataclass(frozen=True)
class OrderId:
    value: UUID

    @classmethod
    def new(cls) -> "OrderId":
        return cls(value=uuid4())

    def __str__(self) -> str:
        return str(self.value)


# domain_models/order.py
from dataclasses import dataclass
from .ids import OrderId, CustomerId

@dataclass(frozen=True)
class Order:
    id: OrderId
    customer_id: CustomerId
    items_total: float
    shipping_cost: float
    status: str  # prefer an Enum for real projects


# domain_models/exceptions.py
class MASABaseError(Exception):
    """All domain exceptions inherit from this."""

class OrderNotFoundError(MASABaseError):
    pass

class StorageUnavailableError(MASABaseError):
    pass

class DuplicateOrderError(MASABaseError):
    pass
```

---

## Engines (Pure Functions)

No classes needed in engines unless grouping related pure functions. Use `mypy --strict`
to verify purity — no `IO` type annotations should appear.

```python
# engines/order_calculator.py
from domain_models.order import Order

def calculate_total(order: Order) -> float:
    """Pure: no I/O, no state, deterministic."""
    return order.items_total + order.shipping_cost

def apply_discount(order: Order, discount_pct: float) -> Order:
    """Returns a new Order with discount applied — immutable transformation."""
    discounted = order.items_total * (1 - discount_pct / 100)
    return Order(
        id=order.id,
        customer_id=order.customer_id,
        items_total=round(discounted, 2),
        shipping_cost=order.shipping_cost,
        status=order.status,
    )
```

---

## Services

Constructor injection only. Use abstract base classes (or `Protocol`) for repository
interfaces so services stay testable without DB.

```python
# services/order_service.py
from typing import Protocol
from domain_models.order import Order
from domain_models.ids import OrderId
from domain_models.exceptions import OrderNotFoundError
from engines.order_calculator import calculate_total


class OrderRepositoryProtocol(Protocol):
    def save(self, order: Order) -> Order: ...
    def find_by_id(self, order_id: OrderId) -> Order: ...


class EmailClientProtocol(Protocol):
    def send_confirmation(self, order: Order) -> None: ...


class OrderService:
    def __init__(
        self,
        repo: OrderRepositoryProtocol,
        email_client: EmailClientProtocol,
    ) -> None:
        self._repo = repo
        self._email_client = email_client

    def create(self, order: Order) -> Order:
        saved = self._repo.save(order)
        total = calculate_total(saved)
        self._email_client.send_confirmation(saved)
        return saved

    def get(self, order_id: OrderId) -> Order:
        return self._repo.find_by_id(order_id)
```

---

## Integrations — Repository Pattern

```python
# integrations/database/models/order_model.py
from sqlalchemy import Column, String, Float, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class OrderModel(Base):
    __tablename__ = "orders"
    pk = Column(Integer, primary_key=True, autoincrement=True)  # internal only
    id = Column(PGUUID(as_uuid=True), unique=True, nullable=False)
    customer_id = Column(PGUUID(as_uuid=True), nullable=False)
    items_total = Column(Float, nullable=False)
    shipping_cost = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)


# integrations/database/repos/order_repo.py
import psycopg2
from sqlalchemy.orm import Session
from domain_models.order import Order
from domain_models.ids import OrderId
from domain_models.exceptions import OrderNotFoundError, StorageUnavailableError
from ..models.order_model import OrderModel


def _to_domain(model: OrderModel) -> Order:
    return Order(
        id=OrderId(value=model.id),
        customer_id=CustomerId(value=model.customer_id),
        items_total=model.items_total,
        shipping_cost=model.shipping_cost,
        status=model.status,
    )


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, order: Order) -> Order:
        try:
            model = OrderModel(
                id=order.id.value,
                customer_id=order.customer_id.value,
                items_total=order.items_total,
                shipping_cost=order.shipping_cost,
                status=order.status,
            )
            self._session.add(model)
            self._session.commit()
            return order
        except psycopg2.OperationalError as e:
            raise StorageUnavailableError("DB unreachable") from e

    def find_by_id(self, order_id: OrderId) -> Order:
        try:
            model = self._session.query(OrderModel).filter_by(id=order_id.value).first()
            if not model:
                raise OrderNotFoundError(f"Order {order_id} not found")
            return _to_domain(model)
        except psycopg2.OperationalError as e:
            raise StorageUnavailableError("DB unreachable") from e
```

---

## Delivery — FastAPI

```python
# delivery/schemas/create_order_request.py
from pydantic import BaseModel
from uuid import UUID, uuid4
from domain_models.order import Order
from domain_models.ids import OrderId, CustomerId


class CreateOrderRequest(BaseModel):
    customer_id: UUID
    items_total: float
    shipping_cost: float

    def to_domain(self) -> Order:
        return Order(
            id=OrderId.new(),
            customer_id=CustomerId(value=self.customer_id),
            items_total=self.items_total,
            shipping_cost=self.shipping_cost,
            status="pending",
        )


# delivery/schemas/create_order_response.py
from pydantic import BaseModel
from uuid import UUID
from domain_models.order import Order


class CreateOrderResponse(BaseModel):
    id: UUID
    status: str

    @classmethod
    def from_domain(cls, order: Order) -> "CreateOrderResponse":
        return cls(id=order.id.value, status=order.status)


# delivery/http/order_handler.py
from fastapi import APIRouter, Depends
from delivery.schemas.create_order_request import CreateOrderRequest
from delivery.schemas.create_order_response import CreateOrderResponse
from services.order_service import OrderService

router = APIRouter(prefix="/orders")


def get_order_service() -> OrderService:
    # Wire dependencies here (or via a DI bootstrap module)
    from integrations.database.repos.order_repo import OrderRepository
    from integrations.external_apis.email_client import EmailClient
    # session = get_session() — inject session from context
    return OrderService(repo=OrderRepository(session=...),
                        email_client=EmailClient())


@router.post("/", response_model=CreateOrderResponse, status_code=201)
async def create_order(
    body: CreateOrderRequest,
    service: OrderService = Depends(get_order_service),
) -> CreateOrderResponse:
    order = service.create(order=body.to_domain())
    return CreateOrderResponse.from_domain(order)
```

---

## Tooling

### import-linter — enforce layer boundaries

```toml
# setup.cfg or pyproject.toml
[importlinter]
root_package = src

[[importlinter:contract]]
name = domain_models has no dependencies
type = forbidden
source_modules = domain_models
forbidden_modules = engines, services, integrations, delivery

[[importlinter:contract]]
name = engines only imports domain_models
type = layers
layers =
    services
    engines
    domain_models

[[importlinter:contract]]
name = delivery never imports engines directly
type = forbidden
source_modules = delivery
forbidden_modules = engines
```

### mypy — static type checking

```ini
[mypy]
strict = True
disallow_untyped_defs = True
disallow_any_generics = True
```

### pytest layout

```
tests/
├── unit/
│   ├── engines/        # no mocks needed — pure functions
│   └── domain_models/  # value object tests
└── integration/
    ├── repos/          # real DB or testcontainers
    └── services/       # mock repos, real service logic
```
