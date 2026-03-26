# MASA in Go — Language-Specific Guide

## Project Layout

Go's package system maps naturally to MASA layers. Each layer is a Go package
(or package group) with an explicit public API.

```
internal/
├── domain/
│   ├── order/
│   │   ├── order.go          # Order struct, OrderStatus type
│   │   └── id.go             # OrderID type
│   └── errors/
│       └── errors.go         # OrderNotFoundError, StorageUnavailableError, …
├── engines/
│   └── ordercalc/
│       └── calculator.go     # CalculateTotal(), ApplyDiscount()
├── services/
│   └── orderservice/
│       ├── service.go        # OrderService struct + methods
│       └── ports.go          # Repository and EmailClient interfaces
├── integrations/
│   ├── database/
│   │   └── orderrepo/
│   │       ├── repo.go       # OrderRepository implementation (PostgreSQL)
│   │       └── mapping.go    # rowToOrder(), orderToRow()
│   └── externalapis/
│       └── emailclient/
│           └── client.go     # EmailClient implementation (SMTP / SendGrid)
└── delivery/
    ├── http/
    │   └── orderhandler/
    │       └── handler.go    # HTTP handler (net/http or Gin)
    └── schemas/
        └── orderschemas/
            ├── request.go    # CreateOrderRequest + ToDomain()
            └── response.go   # CreateOrderResponse + FromDomain()
```

**Package naming rule:** Short, lowercase, domain nouns — `order`, `ordercalc`,
`orderservice`, `orderrepo`. Never `ordercontroller`, `orderhelper`, `orderutil`.

---

## Domain Models

Go structs are naturally immutable when fields are unexported or the struct is
copied on return. Use exported fields for domain models (agents can read them),
but define constructors to enforce invariants.

```go
// internal/domain/order/id.go
package order

import "github.com/google/uuid"

// OrderID is a distinct type — not interchangeable with plain string or uuid.UUID
type OrderID uuid.UUID

func NewOrderID() OrderID {
    return OrderID(uuid.New())
}

func ParseOrderID(s string) (OrderID, error) {
    u, err := uuid.Parse(s)
    if err != nil {
        return OrderID{}, err
    }
    return OrderID(u), nil
}

func (id OrderID) String() string {
    return uuid.UUID(id).String()
}


// internal/domain/order/order.go
package order

type Status string

const (
    StatusPending   Status = "pending"
    StatusConfirmed Status = "confirmed"
    StatusShipped   Status = "shipped"
    StatusCancelled Status = "cancelled"
)

type Order struct {
    ID           OrderID
    CustomerID   CustomerID
    ItemsTotal   float64
    ShippingCost float64
    Status       Status
}


// internal/domain/errors/errors.go
package domainerrors

import "fmt"

type OrderNotFoundError struct {
    ID string
}

func (e *OrderNotFoundError) Error() string {
    return fmt.Sprintf("order %s not found", e.ID)
}

type StorageUnavailableError struct {
    Msg string
}

func (e *StorageUnavailableError) Error() string {
    return e.Msg
}

type DuplicateOrderError struct {
    ID string
}

func (e *DuplicateOrderError) Error() string {
    return fmt.Sprintf("order %s already exists", e.ID)
}
```

---

## Engines (Pure Functions)

Go functions with no pointer receivers on external state, no `io.Reader`/`http.Client`
params. If it's pure, it has no side effects and can be tested with zero setup.

```go
// internal/engines/ordercalc/calculator.go
package ordercalc

import "github.com/yourorg/masa/internal/domain/order"

// CalculateTotal is a pure function — no I/O, no state.
func CalculateTotal(o order.Order) float64 {
    return o.ItemsTotal + o.ShippingCost
}

// ApplyDiscount returns a new Order — original is unchanged (Go value copy).
func ApplyDiscount(o order.Order, discountPct float64) order.Order {
    discounted := o.ItemsTotal * (1 - discountPct/100)
    o.ItemsTotal = math.Round(discounted*100) / 100
    return o // copy returned, original not mutated
}
```

---

## Services — Ports (Interfaces) in the Service Package

In Go, interfaces are defined by the consumer, not the implementor. Define repository
and client interfaces in `services/orderservice/ports.go`. Implement them in
`integrations/`. This is idiomatic Go and maps directly to MASA's Static Dependency
Tracing rule.

```go
// internal/services/orderservice/ports.go
package orderservice

import "github.com/yourorg/masa/internal/domain/order"

// OrderRepository — implemented by integrations/database/orderrepo
type OrderRepository interface {
    Save(o order.Order) (order.Order, error)
    FindByID(id order.OrderID) (order.Order, error)
}

// EmailClient — implemented by integrations/externalapis/emailclient
type EmailClient interface {
    SendConfirmation(o order.Order) error
}


// internal/services/orderservice/service.go
package orderservice

import "github.com/yourorg/masa/internal/domain/order"

type OrderService struct {
    repo        OrderRepository
    emailClient EmailClient
}

// NewOrderService is the constructor — full dependency declaration in one function.
func NewOrderService(repo OrderRepository, emailClient EmailClient) *OrderService {
    return &OrderService{repo: repo, emailClient: emailClient}
}

func (s *OrderService) Create(o order.Order) (order.Order, error) {
    saved, err := s.repo.Save(o)
    if err != nil {
        return order.Order{}, err
    }
    if err := s.emailClient.SendConfirmation(saved); err != nil {
        // decide: fail or log? for now, log and continue
        return saved, nil
    }
    return saved, nil
}

func (s *OrderService) Get(id order.OrderID) (order.Order, error) {
    return s.repo.FindByID(id)
}
```

---

## Integrations — Repository Implementation

```go
// internal/integrations/database/orderrepo/repo.go
package orderrepo

import (
    "database/sql"
    "errors"

    "github.com/yourorg/masa/internal/domain/order"
    domainerrors "github.com/yourorg/masa/internal/domain/errors"
)

type orderRow struct {
    ID           string
    CustomerID   string
    ItemsTotal   float64
    ShippingCost float64
    Status       string
}

func rowToOrder(r orderRow) (order.Order, error) {
    id, err := order.ParseOrderID(r.ID)
    if err != nil {
        return order.Order{}, err
    }
    custID, err := order.ParseCustomerID(r.CustomerID)
    if err != nil {
        return order.Order{}, err
    }
    return order.Order{
        ID:           id,
        CustomerID:   custID,
        ItemsTotal:   r.ItemsTotal,
        ShippingCost: r.ShippingCost,
        Status:       order.Status(r.Status),
    }, nil
}

type OrderRepository struct {
    db *sql.DB
}

func New(db *sql.DB) *OrderRepository {
    return &OrderRepository{db: db}
}

func (r *OrderRepository) FindByID(id order.OrderID) (order.Order, error) {
    row := r.db.QueryRow(
        "SELECT id, customer_id, items_total, shipping_cost, status FROM orders WHERE id = $1",
        id.String(),
    )
    var or orderRow
    if err := row.Scan(&or.ID, &or.CustomerID, &or.ItemsTotal, &or.ShippingCost, &or.Status); err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return order.Order{}, &domainerrors.OrderNotFoundError{ID: id.String()}
        }
        return order.Order{}, &domainerrors.StorageUnavailableError{Msg: err.Error()}
    }
    return rowToOrder(or)
}

func (r *OrderRepository) Save(o order.Order) (order.Order, error) {
    _, err := r.db.Exec(
        "INSERT INTO orders (id, customer_id, items_total, shipping_cost, status) VALUES ($1,$2,$3,$4,$5)",
        o.ID.String(), o.CustomerID.String(), o.ItemsTotal, o.ShippingCost, string(o.Status),
    )
    if err != nil {
        return order.Order{}, &domainerrors.StorageUnavailableError{Msg: err.Error()}
    }
    return o, nil
}
```

---

## Delivery — net/http Handler

```go
// internal/delivery/schemas/orderschemas/request.go
package orderschemas

import (
    "encoding/json"
    "net/http"

    "github.com/yourorg/masa/internal/domain/order"
)

type CreateOrderRequest struct {
    CustomerID   string  `json:"customer_id"`
    ItemsTotal   float64 `json:"items_total"`
    ShippingCost float64 `json:"shipping_cost"`
}

func DecodeCreateOrder(r *http.Request) (CreateOrderRequest, error) {
    var req CreateOrderRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        return CreateOrderRequest{}, err
    }
    return req, nil
}

func (req CreateOrderRequest) ToDomain() (order.Order, error) {
    custID, err := order.ParseCustomerID(req.CustomerID)
    if err != nil {
        return order.Order{}, err
    }
    return order.Order{
        ID:           order.NewOrderID(),
        CustomerID:   custID,
        ItemsTotal:   req.ItemsTotal,
        ShippingCost: req.ShippingCost,
        Status:       order.StatusPending,
    }, nil
}


// internal/delivery/schemas/orderschemas/response.go
package orderschemas

import "github.com/yourorg/masa/internal/domain/order"

type CreateOrderResponse struct {
    ID     string `json:"id"`
    Status string `json:"status"`
}

func FromDomain(o order.Order) CreateOrderResponse {
    return CreateOrderResponse{ID: o.ID.String(), Status: string(o.Status)}
}


// internal/delivery/http/orderhandler/handler.go
package orderhandler

import (
    "encoding/json"
    "net/http"

    domainerrors "github.com/yourorg/masa/internal/domain/errors"
    "github.com/yourorg/masa/internal/delivery/schemas/orderschemas"
    "github.com/yourorg/masa/internal/services/orderservice"
)

type OrderHandler struct {
    service *orderservice.OrderService
}

func New(service *orderservice.OrderService) *OrderHandler {
    return &OrderHandler{service: service}
}

func (h *OrderHandler) Create(w http.ResponseWriter, r *http.Request) {
    // 1. Validate
    req, err := orderschemas.DecodeCreateOrder(r)
    if err != nil {
        http.Error(w, "invalid request body", http.StatusBadRequest)
        return
    }
    domainOrder, err := req.ToDomain()
    if err != nil {
        http.Error(w, "invalid fields", http.StatusBadRequest)
        return
    }
    // 2. Dispatch
    created, err := h.service.Create(domainOrder)
    if err != nil {
        handleDomainError(w, err)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(orderschemas.FromDomain(created))
}

func handleDomainError(w http.ResponseWriter, err error) {
    var notFound *domainerrors.OrderNotFoundError
    if errors.As(err, &notFound) {
        http.Error(w, notFound.Error(), http.StatusNotFound)
        return
    }
    http.Error(w, "internal error", http.StatusInternalServerError)
}
```

---

## Wiring (main.go)

```go
// cmd/api/main.go
package main

import (
    "database/sql"
    "net/http"

    "github.com/yourorg/masa/internal/delivery/http/orderhandler"
    "github.com/yourorg/masa/internal/integrations/database/orderrepo"
    "github.com/yourorg/masa/internal/integrations/externalapis/emailclient"
    "github.com/yourorg/masa/internal/services/orderservice"
)

func main() {
    db, _ := sql.Open("postgres", "...")

    // Compose dependency graph explicitly — MASA Static Dependency Tracing
    repo    := orderrepo.New(db)
    email   := emailclient.New("smtp.example.com")
    service := orderservice.NewOrderService(repo, email)
    handler := orderhandler.New(service)

    mux := http.NewServeMux()
    mux.HandleFunc("POST /orders", handler.Create)
    http.ListenAndServe(":8080", mux)
}
```

The dependency graph is fully readable from `main.go` alone. No magic, no reflection.

---

## Tooling

### Layer boundary enforcement — depguard (golangci-lint)

```yaml
# .golangci.yml
linters-settings:
  depguard:
    rules:
      engines-cannot-import-integrations:
        files: ["**/engines/**/*.go"]
        deny:
          - pkg: "github.com/yourorg/masa/internal/integrations"
            desc: "engines must not import integrations"
      delivery-cannot-import-engines:
        files: ["**/delivery/**/*.go"]
        deny:
          - pkg: "github.com/yourorg/masa/internal/engines"
            desc: "delivery must access engines through services only"
```

### Testing layout

```
tests/
├── unit/
│   └── engines/        # table-driven pure function tests (zero setup)
└── integration/
    ├── repos/          # testcontainers-go for real PostgreSQL
    └── services/       # mock interfaces with testify/mock
```

### Interface mocking

```go
// Use mockery or testify/mock to generate mocks from service ports:
// go install github.com/vektra/mockery/v2@latest
// mockery --name=OrderRepository --dir=internal/services/orderservice --output=tests/mocks
```
