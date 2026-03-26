# MASA Validation — Compliance Checklist and Violation Catalog

Use this reference when running `/masa:validate` or `/masa:audit`.

---

## Layer-by-Layer Compliance Checklist

Run each check for the relevant layer. A ✗ in any check is a violation.

### `domain_models/`

| Check | Pass condition |
|---|---|
| No imports from `engines/`, `services/`, `integrations/`, `delivery/` | Zero cross-layer imports |
| All classes/structs/interfaces are pure data (no methods with side effects) | Only getters, validators, factory methods |
| All IDs are typed value objects | No bare `int`, `str`, `string` used as identifiers |
| All domain exceptions defined here | No `raise Exception("...")` in business layers |
| No ORM decorators / DB annotations | No SQLAlchemy Base, TypeORM Entity, GORM tags |

### `engines/`

| Check | Pass condition |
|---|---|
| Imports only from `domain_models/` | Zero imports from other layers |
| All functions are pure (no I/O, no DB, no HTTP) | No `open()`, `requests`, `psycopg2`, `fetch`, `http.Get` |
| All functions are stateless | No instance-level mutable state that persists between calls |
| All inputs and outputs are domain models | No raw `dict`, `any`, `interface{}`, JSON types |
| No dependency injection needed | Functions take domain models, return domain models |

### `services/`

| Check | Pass condition |
|---|---|
| Imports from `domain_models/`, `engines/`, `integrations/repos or external_apis` only | No direct import from `integrations/database/models/` |
| No direct DB queries | All DB access via repository interfaces |
| No raw external types in method signatures | All params/returns are domain models |
| All dependencies declared in constructor | No module-level singletons, no `Depends()` magic |
| No HTTP-specific types (request/response objects) | No FastAPI `Request`, Express `req`, Go `http.Request` |

### `integrations/database/models/`

| Check | Pass condition |
|---|---|
| Never imported outside `integrations/database/` | Zero imports from `services/`, `engines/`, `delivery/` |
| ORM/schema types only | Contains only table definitions, no business logic |

### `integrations/database/repos/`

| Check | Pass condition |
|---|---|
| Imports from `domain_models/` and `integrations/database/models/` only | No business logic imports |
| All infrastructure exceptions caught and re-raised as domain exceptions | No raw `psycopg2`, `sql.ErrNoRows`, `DatabaseError` leaking to callers |
| Returns domain models, never ORM entities | `find_by_id` returns `Order`, not `OrderModel` |
| DB auto-increment IDs never returned | Only domain UUIDs / business tags in return values |

### `integrations/external_apis/`

| Check | Pass condition |
|---|---|
| All third-party SDK exceptions caught and re-raised as domain exceptions | Same pattern as repos |
| Returns domain models, never SDK response objects | `StripeClient.charge()` returns `PaymentResult`, not `stripe.Charge` |

### `delivery/http/` (handlers)

| Check | Pass condition |
|---|---|
| Each handler has exactly two operations: validate + dispatch | No `if/else` business logic |
| No direct imports from `engines/` | All business access via `services/` |
| No direct imports from `integrations/` | No repository calls in handlers |
| All request parsing done via schema objects | No manual `request.body["field"]` access |

### `delivery/schemas/`

| Check | Pass condition |
|---|---|
| Never imported outside `delivery/` | Zero imports from `services/`, `engines/`, `integrations/` |
| Contains only DTOs with `.to_domain()` / `.from_domain()` methods | No business logic in schema classes |

---

## Violation Catalog

Each violation has a canonical name, symptom, root cause, and fix.

---

### V-01: Raw Type Leak
**Rule violated:** Data Dressing (Rule 1)
**Symptom:** A `dict`, `map[string]interface{}`, `Record<string, unknown>`, or `any` appears as a parameter or return type in `engines/` or `services/`.
**Root cause:** Data was not dressed at the boundary — raw format carried into business logic.
**Fix:** Identify where data enters the system (HTTP body, DB row, API response). Create a domain model. Add a mapping function at the boundary. Update function signatures.

---

### V-02: Hidden Dependency
**Rule violated:** Static Dependency Tracing (Rule 2)
**Symptom:** A class uses a service/repository/client that does not appear in its constructor. Source: module-level variable, `container.get()`, `@Inject()`, global `import`.
**Root cause:** Dependency resolved outside the constructor — invisible to static analysis.
**Fix:** Add the dependency as a constructor parameter. Remove the global/decorator reference. Update all instantiation call sites.

---

### V-03: Fat Handler
**Rule violated:** Anemic Delivery (Rule 3)
**Symptom:** A route handler contains `if/else` branches on business conditions, direct DB calls, or more than ~10 lines of logic.
**Root cause:** Business logic accumulated in the delivery layer over time.
**Fix:** Extract all business logic into a new or existing service method. Handler calls service, service contains the logic.

---

### V-04: Infrastructure Exception Leak
**Rule violated:** Semantic Error Handling (Rule 4)
**Symptom:** A `try/except` in `services/` or `engines/` catches `psycopg2.Error`, `sql.ErrNoRows`, `AxiosError`, or any SDK-specific exception type.
**Root cause:** Exception not caught and translated in the `integrations/` layer.
**Fix:** Add a `try/except` in the relevant repo or client. Catch the infrastructure exception. Re-raise as the appropriate domain exception from `domain_models/exceptions`.

---

### V-05: Auto-Increment ID Leak
**Rule violated:** ID Encapsulation (Rule 5)
**Symptom:** An `int`, `INT`, or `BIGINT` ID appears in a service method signature, engine function, or domain model.
**Root cause:** DB-generated PK used as a domain identifier.
**Fix:** Introduce a `UUID`-based domain ID in `domain_models/ids`. Update the DB schema to include a UUID column alongside the PK. Update repos to use the UUID when communicating upward.

---

### V-06: Cross-Layer Import
**Rule violated:** Architecture Pillar (Pillar 4)
**Symptom:** A file in `engines/` imports from `services/`, `integrations/`, or `delivery/`. Or `delivery/` imports from `engines/` directly.
**Root cause:** Layer boundary broken — likely a shortcut during initial development.
**Fix:** Move the needed logic to the correct layer, or pass it as a parameter. Never adjust the import to work around the violation.

---

### V-07: Technical Folder Name
**Rule violated:** Semantics Pillar (Pillar 3)
**Symptom:** A top-level folder named `controllers/`, `utils/`, `helpers/`, `core/`, `common/`, `base/`, `shared/`.
**Root cause:** Role-based naming used instead of domain-based naming.
**Fix:** Identify the business concepts served by the folder's contents. Rename to a domain noun phrase. If contents serve multiple domains, split into multiple domain-named folders.

---

### V-08: ORM Entity in Service
**Rule violated:** Data Dressing (Rule 1) + Architecture (Pillar 4)
**Symptom:** A SQLAlchemy model, TypeORM entity, or GORM struct appears as a parameter or return type in `services/`.
**Root cause:** Repository returns ORM entity instead of domain model, or service calls ORM directly.
**Fix:** Update the repository to map ORM entities to domain models before returning. If the service calls ORM directly, extract to a repository.

---

## Auto-Detection Hints

When auditing code, look for these import/code patterns as fast violation signals:

| Pattern | Likely violation |
|---|---|
| `from integrations.database.models import` in `services/` | V-08 or V-06 |
| `from engines import` in `delivery/` | V-06 |
| `except psycopg2` / `except DatabaseError` in `services/` | V-04 |
| `def process(data: dict)` in `services/` or `engines/` | V-01 |
| `= container.get(` / `@Inject(` / global `= SomeService()` | V-02 |
| `if request.body` / SQL query in handler | V-03 |
| `id: int` in domain model or service signature | V-05 |
| Folder named `utils/`, `helpers/`, `common/` at src root | V-07 |

---

## Compliance Score (for /masa:audit)

When auditing a full layer, report:

```
Layer: services/
Files audited: N
Violations found: X
  - V-01 Raw Type Leak: [filename:line]
  - V-02 Hidden Dependency: [filename:line]
  ...
Compliance score: (N_clean_files / N_total_files) × 100%
```
