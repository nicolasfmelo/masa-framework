# MASA Rulesets — Complete Reference with Code Examples

Each ruleset is presented with: **Motivation** (what agent failure it prevents),
**Design** (the rule), and **Technical Advantage** (why this beats alternatives).
Code examples are provided for Python, TypeScript, and Go.

---

## Rule 1: Data Dressing Principle

### Motivation
When raw external types (dicts, JSON objects, ORM rows, API responses) flow into
business logic, agents cannot verify field names statically. A `dict` in a service
function could represent any domain concept — agents hallucinate field names and
introduce silent `KeyError` / `undefined` bugs.

### Design
All external data must be **dressed** (mapped) into a typed `domain_model` immediately
upon crossing the `delivery` or `integrations` boundary. Raw external types are
forbidden inside `engines/` and `services/`.

### Technical Advantage
Agents operating in `engines/` and `services/` can assume all inputs are fully-typed
domain objects. Type checkers (mypy, tsc, Go compiler) verify field access statically.

---

### Python

```python
# domain_models/order.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class Order:
    id: UUID
    customer_id: UUID
    items_total: float
    shipping_cost: float

# ✗ VIOLATION — raw dict in service
# services/order_service.py
def process_order(raw: dict) -> None:
    total = raw["items_total"] + raw["shipping"]  # agent cannot verify keys

# ✓ MASA-COMPLIANT — domain model in service
# services/order_service.py
def process_order(order: Order) -> None:
    total = order.items_total + order.shipping_cost  # statically verified

# integrations/database/repos/order_repo.py  — dressing happens HERE
def find_by_id(self, order_id: UUID) -> Order:
    row = self._db.query("SELECT * FROM orders WHERE id = %s", str(order_id))
    return Order(
        id=UUID(row["id"]),
        customer_id=UUID(row["customer_id"]),
        items_total=float(row["items_total"]),
        shipping_cost=float(row["shipping_cost"]),
    )
```

### TypeScript

```typescript
// domain_models/order.ts
export interface Order {
  readonly id: string;          // UUID
  readonly customerId: string;
  readonly itemsTotal: number;
  readonly shippingCost: number;
}

// ✗ VIOLATION — unknown/any in service
// services/order.service.ts
function processOrder(raw: Record<string, unknown>): void {
  const total = (raw.itemsTotal as number) + (raw.shippingCost as number); // unsafe cast
}

// ✓ MASA-COMPLIANT
// services/order.service.ts
function processOrder(order: Order): void {
  const total = order.itemsTotal + order.shippingCost; // tsc verifies this
}

// integrations/database/repos/order.repo.ts — dress on exit from DB
function toOrder(row: OrderRow): Order {
  return {
    id: row.id,
    customerId: row.customer_id,
    itemsTotal: Number(row.items_total),
    shippingCost: Number(row.shipping_cost),
  };
}
```

### Go

```go
// domain_models/order.go
package order

import "github.com/google/uuid"

type Order struct {
    ID           uuid.UUID
    CustomerID   uuid.UUID
    ItemsTotal   float64
    ShippingCost float64
}

// ✗ VIOLATION — map[string]interface{} in service
// services/order_service.go
func ProcessOrder(raw map[string]interface{}) error {
    total := raw["items_total"].(float64) + raw["shipping_cost"].(float64) // unsafe assertion
    _ = total
    return nil
}

// ✓ MASA-COMPLIANT
// services/order_service.go
func ProcessOrder(o order.Order) error {
    total := o.ItemsTotal + o.ShippingCost // compiler-verified
    _ = total
    return nil
}

// integrations/database/repos/order_repo.go — dress DB row into domain model
func rowToOrder(row *sqlx.Row) (order.Order, error) {
    var r orderRow
    if err := row.StructScan(&r); err != nil {
        return order.Order{}, err
    }
    return order.Order{
        ID:           uuid.MustParse(r.ID),
        CustomerID:   uuid.MustParse(r.CustomerID),
        ItemsTotal:   r.ItemsTotal,
        ShippingCost: r.ShippingCost,
    }, nil
}
```

---

## Rule 2: Static Dependency Tracing

### Motivation
DI frameworks (Spring, Angular, FastAPI `Depends`) resolve dependencies at runtime.
From a static analysis perspective, these create invisible edges in the dependency
graph — edges that exist only while the application is running. Agents cannot build
an accurate dependency map without executing the program.

### Design
All dependencies (repositories, API clients, configuration) are passed as **explicit
constructor parameters**. Framework-managed injection, global service locators, and
module-level singletons are forbidden.

### Technical Advantage
An agent reading a constructor signature gets the complete, accurate dependency list
in one line — a purely syntactic operation with zero runtime required.

---

### Python

```python
# ✗ VIOLATION — hidden dependency via global
# services/order_service.py
_repo = OrderRepository()  # module-level singleton

class OrderService:
    def create(self, order: Order) -> Order:
        return _repo.save(order)  # dependency invisible from class definition

# ✓ MASA-COMPLIANT — explicit constructor injection
# services/order_service.py
class OrderService:
    def __init__(self, repo: OrderRepository, email_client: EmailClient) -> None:
        self._repo = repo
        self._email_client = email_client
    # Agent reads ONE line: this service needs a repo and an email client. Done.
```

### TypeScript

```typescript
// ✗ VIOLATION — NestJS @Inject() magic
@Injectable()
export class OrderService {
  @Inject(OrderRepository) private repo: OrderRepository; // invisible to static reader
}

// ✓ MASA-COMPLIANT — constructor injection (works with or without frameworks)
export class OrderService {
  constructor(
    private readonly repo: OrderRepository,
    private readonly emailClient: EmailClient,
  ) {}
  // Full dependency graph: one glance at constructor params
}
```

### Go

```go
// ✗ VIOLATION — global variable
// services/order_service.go
var globalRepo = newOrderRepo() // hidden dependency

type OrderService struct{}

func (s *OrderService) Create(o order.Order) error {
    return globalRepo.Save(o) // agent cannot see this dependency
}

// ✓ MASA-COMPLIANT — injected via struct fields, set at construction
// services/order_service.go
type OrderService struct {
    repo        OrderRepository
    emailClient EmailClient
}

func NewOrderService(repo OrderRepository, emailClient EmailClient) *OrderService {
    return &OrderService{repo: repo, emailClient: emailClient}
}
// Constructor function = complete dependency declaration
```

---

## Rule 3: Anemic Delivery Layer

### Motivation
Fat controllers accumulate business logic over time, forcing agents to read handler
code to understand business behavior. This doubles the file search space for any
business-rule retrieval task.

### Design
`delivery/` handlers perform **exactly two operations**: (1) validate incoming schema,
(2) call the appropriate service. Conditional business logic, data transformations, and
direct repository calls are forbidden in handlers.

### Technical Advantage
Agents searching for business rules can skip `delivery/` entirely, reducing the
candidate file set to `engines/` and `services/` only.

---

### Python (FastAPI)

```python
# ✗ VIOLATION — business logic in handler
@router.post("/orders")
async def create_order(body: CreateOrderRequest, db: Session = Depends(get_db)):
    # ← business logic and DB call directly in handler
    if body.items_total < 0:
        raise HTTPException(400, "Negative total")
    order = db.query(OrderModel).filter_by(customer_id=body.customer_id).first()
    if order:
        raise HTTPException(409, "Duplicate")
    ...

# ✓ MASA-COMPLIANT — thin handler
@router.post("/orders")
async def create_order(
    body: CreateOrderRequest,
    service: OrderService = Depends(get_order_service),
) -> CreateOrderResponse:
    order = await service.create(order=body.to_domain())
    return CreateOrderResponse.from_domain(order)
```

### TypeScript (Express / Fastify)

```typescript
// ✗ VIOLATION
app.post('/orders', async (req, res) => {
  if (req.body.itemsTotal < 0) { res.status(400).json({error: 'bad total'}); return; }
  const existing = await db.query('SELECT * FROM orders WHERE ...');
  // ... more business logic
});

// ✓ MASA-COMPLIANT
app.post('/orders', async (req, res) => {
  const body = CreateOrderSchema.parse(req.body);   // validate
  const order = await orderService.create(body.toDomain()); // dispatch
  res.status(201).json(CreateOrderResponse.from(order));
});
```

### Go (net/http / Gin)

```go
// ✗ VIOLATION
func CreateOrderHandler(w http.ResponseWriter, r *http.Request) {
    var body CreateOrderRequest
    json.NewDecoder(r.Body).Decode(&body)
    if body.ItemsTotal < 0 { /* business logic here */ }
    // DB call here
}

// ✓ MASA-COMPLIANT
func (h *OrderHandler) Create(w http.ResponseWriter, r *http.Request) {
    var body CreateOrderRequest
    if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
        http.Error(w, "invalid request", http.StatusBadRequest)
        return
    }
    created, err := h.service.Create(body.ToDomain())
    if err != nil { handleDomainError(w, err); return }
    json.NewEncoder(w).Encode(CreateOrderResponse{}.FromDomain(created))
}
```

---

## Rule 4: Semantic Error Handling

### Motivation
Library-specific exceptions (`psycopg2.OperationalError`, `sql.ErrNoRows`,
`AxiosError`) leaking into service layers force agents to understand third-party
SDK internals in order to reason about business error flows.

### Design
Infrastructure exceptions are caught **exclusively inside `integrations/`** and
re-raised as Domain Exceptions defined in `domain_models/exceptions`. Service and
engine layers handle only domain exceptions.

### Technical Advantage
Agents in `services/` encounter only business-vocabulary errors. No SDK knowledge required.

---

### Python

```python
# domain_models/exceptions.py
class OrderNotFoundError(Exception): pass
class StorageUnavailableError(Exception): pass

# integrations/database/repos/order_repo.py  — catch here, re-raise as domain
import psycopg2
from domain_models.exceptions import OrderNotFoundError, StorageUnavailableError

def find_by_id(self, order_id: UUID) -> Order:
    try:
        row = self._db.fetchone("SELECT * FROM orders WHERE id = %s", str(order_id))
        if not row:
            raise OrderNotFoundError(f"Order {order_id} not found")
        return row_to_order(row)
    except psycopg2.OperationalError as e:
        raise StorageUnavailableError("Order store unreachable") from e

# services/order_service.py — handles only domain exceptions
from domain_models.exceptions import OrderNotFoundError
def get_order(self, order_id: UUID) -> Order:
    try:
        return self._repo.find_by_id(order_id)
    except OrderNotFoundError:
        raise  # re-raise as-is — already domain vocabulary
```

### TypeScript

```typescript
// domain_models/exceptions.ts
export class OrderNotFoundError extends Error {
  constructor(id: string) { super(`Order ${id} not found`); }
}
export class StorageUnavailableError extends Error {}

// integrations/database/repos/order.repo.ts
import { DatabaseError } from 'pg';
import { OrderNotFoundError, StorageUnavailableError } from '../../domain_models/exceptions';

async findById(id: string): Promise<Order> {
  try {
    const row = await this.db.query('SELECT * FROM orders WHERE id = $1', [id]);
    if (!row.rows[0]) throw new OrderNotFoundError(id);
    return toOrder(row.rows[0]);
  } catch (e) {
    if (e instanceof DatabaseError) throw new StorageUnavailableError(e.message);
    throw e;
  }
}
```

### Go

```go
// domain_models/errors.go
package domainerrors

import "fmt"

type OrderNotFoundError struct{ ID string }
func (e *OrderNotFoundError) Error() string { return fmt.Sprintf("order %s not found", e.ID) }

type StorageUnavailableError struct{ Msg string }
func (e *StorageUnavailableError) Error() string { return e.Msg }

// integrations/database/repos/order_repo.go
func (r *orderRepo) FindByID(id uuid.UUID) (order.Order, error) {
    row := r.db.QueryRow("SELECT * FROM orders WHERE id = $1", id)
    var o orderRow
    if err := row.Scan(&o); err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return order.Order{}, &domainerrors.OrderNotFoundError{ID: id.String()}
        }
        return order.Order{}, &domainerrors.StorageUnavailableError{Msg: err.Error()}
    }
    return rowToOrder(o), nil
}
```

---

## Rule 5: ID Encapsulation

### Motivation
Database auto-increment IDs couple identity to persistence technology. When an integer
row ID flows through services and engines, any refactoring of the storage backend
silently breaks identity assumptions. Agents working across layers cannot determine
whether an `int` is a domain identity or an internal DB artifact.

### Design
All business logic uses **Domain IDs** (UUIDs or semantic business tags like `"ORD-2026-001"`).
DB auto-increments are generated and consumed exclusively within `integrations/database/repos/`.
Domain IDs are typed value objects, not bare `int` or `str`/`string`.

### Technical Advantage
The type system makes the distinction between `OrderId` and `int` explicit and
statically enforceable. Agents never need to reason about DB-layer identity management
when working in `engines/` or `services/`.

---

### Python

```python
# domain_models/ids.py
from uuid import UUID, uuid4
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderId:
    value: UUID
    @classmethod
    def new(cls) -> "OrderId": return cls(value=uuid4())
    def __str__(self) -> str: return str(self.value)

# integrations/database/models/order_model.py — DB auto-increment stays here
class OrderModel(Base):
    __tablename__ = "orders"
    pk = Column(Integer, primary_key=True, autoincrement=True)  # internal only
    id = Column(UUID(as_uuid=True), unique=True, nullable=False)  # domain id

# ✗ VIOLATION — int leaking into service
# services/order_service.py
def get_order(self, order_pk: int) -> Order: ...  # int = DB concern, wrong layer

# ✓ MASA-COMPLIANT
# services/order_service.py
def get_order(self, order_id: OrderId) -> Order: ...  # typed domain ID
```

### TypeScript

```typescript
// domain_models/ids.ts
type Brand<T, B extends string> = T & { readonly __brand: B };
export type OrderId = Brand<string, 'OrderId'>; // UUID string, branded
export const OrderId = {
  new: (): OrderId => crypto.randomUUID() as OrderId,
  from: (raw: string): OrderId => raw as OrderId,
};

// ✗ VIOLATION
function getOrder(orderId: number): Promise<Order> { ... } // number = DB internal

// ✓ MASA-COMPLIANT
function getOrder(orderId: OrderId): Promise<Order> { ... }
```

### Go

```go
// domain_models/ids.go
package domainids

import "github.com/google/uuid"

type OrderID uuid.UUID // distinct type, not just an alias for string/int
func NewOrderID() OrderID { return OrderID(uuid.New()) }
func (id OrderID) String() string { return uuid.UUID(id).String() }

// ✗ VIOLATION
func GetOrder(orderPK int) (order.Order, error) { ... } // int = DB row ID

// ✓ MASA-COMPLIANT
func GetOrder(id domainids.OrderID) (order.Order, error) { ... }
```
