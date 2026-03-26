# MASA Pillars — Deep Reference

## Overview

The four MASA pillars are not independent guidelines — they are a unified system.
Removing any one pillar degrades cognizability for AI agents.

---

## Pillar 1: Modularity — Radical Isolation

**Operational definition:** Every module (a file or folder unit) has exactly one
responsibility, declared entry points (public functions/classes), and declared exit
points (return types / raised exceptions). No module reaches into another module's
internals.

**What it means for code generation:**
- One class or one cohesive group of pure functions per file
- No circular imports — ever
- Public surface area is minimized: only export what callers need
- Shared mutable state between modules is forbidden

**Anti-patterns (never generate these):**
- A single `utils.py` / `helpers.ts` / `util.go` file that accumulates unrelated functions
- A module that imports from a sibling module's internal helpers
- Circular dependency chains between any two modules

**Why it matters for agents:**
Radical isolation means the impact surface of any change is bounded and visible.
An agent modifying module A can enumerate its effects by reading module A's exports
and the one-directional import graph — nothing hidden.

---

## Pillar 2: Agency — Cognizability-First

**Operational definition:** The codebase must be statically interpretable by an AI
agent operating with only the directory tree and source files (no execution, no docs,
no runtime). An agent should be able to answer:
- What business concern does this file address?
- What are this module's dependencies?
- What layer does this file belong to?
- Is this proposed change architecturally valid?

...purely from file paths and constructor/function signatures.

**What it means for code generation:**
- Every name (file, folder, class, function) encodes intent, not implementation
- Constructor signatures are complete dependency declarations
- No hidden state, no global singletons, no ambient context
- Exception types encode business meaning, not infrastructure details

**Anti-patterns (never generate these):**
- `get_data()`, `process()`, `handle()` — verbs without domain nouns
- `Manager`, `Helper`, `Processor` suffix classes with unclear scope
- Module-level singletons that are implicitly shared across callers
- Functions with side effects that are not declared in their signature

**Cognizability test:** Before finalizing any generated file, ask:
*"If an agent saw only this file's path and import list, would it know exactly what
business problem this file solves and what it depends on?"*
If the answer is "not exactly" — rename or restructure.

---

## Pillar 3: Semantics — Domain-Driven Naming

**Operational definition:** Folder and file names must express the **business domain**
they serve, not the technical pattern they implement. A new developer (or agent) reading
the directory tree should be able to describe the business problem the system solves
without opening any file.

**Naming rules:**
- Folders: business nouns or noun phrases (`order_processing/`, `payment_gateway/`,
  `user_authentication/`, `inventory_counting/`)
- Files: the specific business concept they represent (`order.py`, `payment_method.go`,
  `invoice_calculator.ts`)
- Classes/structs: domain entity names (`Order`, `PaymentMethod`, `InvoiceLineItem`)
- Functions: verb + domain noun (`calculate_total`, `submit_order`, `fetch_invoice`)

**Anti-patterns (never generate these):**
- `controllers/`, `services/`, `repositories/`, `factories/`, `utils/`, `helpers/`,
  `core/`, `common/`, `base/`, `shared/` as top-level folder names
- `BaseService`, `AbstractRepository`, `GenericHandler` — technical meta-names
- `data`, `info`, `result`, `response` as variable names without domain qualification

**Language-specific note:**
In Go, package names are short lowercase nouns — prefer `order`, `payment`, `invoice`
over `orderservice`, `paymenthelper`.

---

## Pillar 4: Architecture — Strict Layered Structure

**Operational definition:** The five-layer hierarchy enforces a single rule:
**dependencies flow inward only**. Each layer may import from layers below it;
no layer may import from a layer above it or at the same level (except within
the same layer's own folder).

**Layer dependency matrix:**

| Layer | May import from |
|---|---|
| `domain_models` | Nothing (no imports from src/) |
| `engines` | `domain_models` only |
| `services` | `domain_models`, `engines`, `integrations` |
| `integrations` | `domain_models` only (for models/repos) |
| `delivery` | `domain_models`, `services` (schemas may import `domain_models`) |

**What it means for code generation:**
- Always check the import statement before finalizing any file
- If a file in `engines/` needs to call a repository, it must be refactored: the
  repository call belongs in `services/`, passed as a parameter to the engine
- A `delivery/` handler that contains business logic is always wrong

**Anti-patterns (never generate these):**
- An `engines/` file that imports from `integrations/` or `services/`
- A `services/` file that imports directly from `integrations/database/models/`
  (must go through `repos/`)
- A `delivery/` file that imports from `engines/` directly (must go through `services/`)
- Any file that imports from `delivery/`

**Enforcement tooling by language:**
- Python: `import-linter` with layered contracts
- TypeScript: ESLint `no-restricted-imports` rules + path aliases
- Go: custom `go vet` plugin or `golangci-lint` with `depguard`
