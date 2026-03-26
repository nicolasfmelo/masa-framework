# MASA Task Execution Protocol

## Overview

Every feature implementation in a MASA codebase follows a strict **five-step protocol**
in bottom-up layer order. The protocol is not optional — skipping steps or reversing
order introduces layer violations.

The key insight: layers with fewer dependencies are implemented first. This makes each
step independently testable and eliminates the circular reading loops agents encounter
in conventional codebases.

---

## The Five Steps

```
Step 1: domain_models/   ← no dependencies (start here always)
Step 2: engines/         ← depends on domain_models only
Step 3: integrations/    ← depends on domain_models only
Step 4: services/        ← depends on domain_models + engines + integrations
Step 5: delivery/        ← depends on domain_models + services
```

---

## Step-by-Step Protocol

### Step 1 — Domain Review (`domain_models/`)

**Goal:** Establish the business vocabulary for the feature before writing any logic.

Actions:
1. Identify the domain concepts involved (entities, value objects, IDs, events)
2. Create or update data structures in `domain_models/`
3. Define any new Domain Exceptions in `domain_models/exceptions`
4. Define typed IDs if new entities are introduced

**Checklist before moving to Step 2:**
- [ ] All domain concepts have typed representations
- [ ] No imports from other layers
- [ ] No ORM annotations or infrastructure concerns
- [ ] Domain exceptions defined for all expected error cases

---

### Step 2 — Engine Draft (`engines/`)

**Goal:** Implement pure business logic as stateless functions.

Actions:
1. Identify the calculation, transformation, or business rule at the core of the feature
2. Write pure functions that take domain models and return domain models
3. Write unit tests — engines require no mocks (no I/O)

**Checklist before moving to Step 3:**
- [ ] All functions are pure (no I/O, no state)
- [ ] All inputs/outputs are domain models
- [ ] Imports from `domain_models/` only
- [ ] Unit tested without any infrastructure setup

**Decision node — does this feature have no pure logic?**
If the feature is purely orchestration (fetch + transform + save), Step 2 produces
an empty file or no file. Proceed to Step 3. Do not invent artificial engine logic.

---

### Step 3 — Integration Preparation (`integrations/`)

**Goal:** Build the infrastructure adapters the service will need.

Actions:
1. If new data needs persistence: create/update `integrations/database/models/` and
   `integrations/database/repos/`
2. If external APIs are involved: create/update `integrations/external_apis/`
3. Implement all infrastructure exception → domain exception translations here

**Checklist before moving to Step 4:**
- [ ] Repository/client returns domain models, not ORM/SDK types
- [ ] All infrastructure exceptions caught and re-raised as domain exceptions
- [ ] DB auto-increments stay internal; domain UUIDs exposed upward
- [ ] Integration tests or mocks can verify these in isolation

---

### Step 4 — Orchestration (`services/`)

**Goal:** Compose the business flow using engines and integrations.

Actions:
1. Create or update the service class
2. Declare all dependencies (repos, clients, other services) as constructor parameters
3. Implement the use-case method: call repos → dress data → call engines → save results
4. Handle domain exceptions where appropriate

**Checklist before moving to Step 5:**
- [ ] All dependencies are constructor parameters (no globals, no DI magic)
- [ ] All data entering engine calls is a domain model (no raw types)
- [ ] No direct DB calls — all via repository interfaces
- [ ] No HTTP-specific types in method signatures

**Service method skeleton:**
```python
def execute_feature(self, domain_input: DomainInput) -> DomainOutput:
    # 1. Fetch what we need
    existing = self._repo.find_by_id(domain_input.id)
    # 2. Apply business logic (engine)
    result = calculate_something(existing, domain_input)
    # 3. Persist result
    saved = self._repo.save(result)
    # 4. Side effects (notifications, events)
    self._email_client.send_confirmation(saved)
    return saved
```

---

### Step 5 — Exposure (`delivery/`)

**Goal:** Expose the feature via the transport protocol (HTTP, CLI, events).

Actions:
1. Create a request/response schema in `delivery/schemas/` with `.to_domain()` / `.from_domain()`
2. Add a thin route handler in `delivery/http/` that validates + dispatches
3. Wire the service in the dependency setup (main.py, bootstrap, wire.go)

**Checklist:**
- [ ] Handler has exactly 2 operations: validate schema + call service
- [ ] No business logic or conditional branches in handler
- [ ] Request schema maps to domain model in `to_domain()`
- [ ] Response schema maps from domain model in `from_domain()`
- [ ] Handler does not import from `engines/` or `integrations/` directly

---

## Boundary Violation Detection

During any step, if you find yourself wanting to:

| Urge | This means | Correct action |
|---|---|---|
| Import a DB model into `services/` | Missing repo translation | Add mapping in `repos/`, expose domain model |
| Call a DB query directly in `services/` | Repo not yet created | Create repo in Step 3, inject in service |
| Add business logic in a handler | Missing service method | Extract to service in Step 4 |
| Import from `engines/` in `delivery/` | Handler bypassing service | Route through `services/` |
| Use a raw `dict` in an engine | Missing domain model | Add to `domain_models/` in Step 1 |
| Pass an `int` DB ID to a service | ID not encapsulated | Introduce typed domain ID in Step 1 |

**Always fix at the correct layer. Never adjust the import to work around the violation.**

---

## Feature Implementation Walkthrough Example

**Feature:** "Create a new order from an HTTP POST request"

```
Step 1 — domain_models/
  + order.py          → Order dataclass with OrderId, items_total, shipping_cost
  + ids.py            → OrderId(UUID) typed value object
  + exceptions.py     → DuplicateOrderError, StorageUnavailableError

Step 2 — engines/
  + order_calculator.py → calculate_total(order: Order) -> float (pure function)

Step 3 — integrations/
  + database/models/order_model.py → SQLAlchemy OrderModel (pk + uuid + fields)
  + database/repos/order_repo.py   → OrderRepository.save(Order) -> Order
                                      (catches psycopg2 → re-raises StorageUnavailableError)

Step 4 — services/
  + order_service.py → OrderService(repo: OrderRepository)
                        .create(order: Order) -> Order
                        (dresses input, calls calculator, saves via repo)

Step 5 — delivery/
  + schemas/create_order_request.py → CreateOrderRequest + .to_domain()
  + schemas/create_order_response.py → CreateOrderResponse + .from_domain()
  + http/order_handler.py           → POST /orders → validate → service.create()
```

Total files for a complete feature: ~7–9 files, each with a single clear responsibility.
An agent can regenerate any one of them from its file path alone.
