# MASA — Modular Agentic Semantic Architecture

> An architecture framework designed to maximize **cognizability** — the degree to which AI agents can understand, navigate, and safely modify a codebase through static inspection alone.

📄 **Read the full study:** [www.masa-framework.org](https://www.masa-framework.org/)

---

## Why MASA?

AI coding agents (Copilot, Cursor, SWE-agent, Devin, etc.) are becoming first-class participants in software development. Yet most architectural patterns were designed for *human* comprehension. MASA flips the design lens: **what if we optimized code organization for the way agents actually read and reason about code?**

The result is measurable. In controlled experiments across three complexity tiers:

| | MASA | Baseline (DDD/Clean) |
|---|---|---|
| **Cognizability Score (C_core)** | 0.74 – 0.83 | 0.62 – 0.75 |
| **Architectural Violations** | **0** | 1 – 22 |
| **Task Pass Rate** | 100% | 100% |
| **Relative Improvement** | **+30–35%** | — |

Agents complete tasks equally well in both architectures — but MASA-structured code **preserves architectural integrity** while baseline code accumulates violations with every edit.

## The Four Pillars

| # | Pillar | What It Means |
|---|--------|---------------|
| 1 | **Semantic Naming** | Every file, class, and function name conveys *intent*, not technical role. `PaymentRiskEngine`, not `Utils`. |
| 2 | **Static Dependency Traceability** | All dependencies are explicit imports — no magic, no runtime injection, no service locators. |
| 3 | **Infrastructure Isolation** | Business logic never imports infrastructure. Databases, APIs, and frameworks live behind clear boundaries. |
| 4 | **Layer Enforcement** | Strict unidirectional dependency flow: Domain → Engine → Service → Integration/Delivery. |

📖 Deep dive: [`specification/references/pillars.md`](specification/references/pillars.md)

## The Five-Layer Architecture

```
┌─────────────────────────────────────────────┐
│  Delivery        HTTP handlers, CLI, events │  ← Entry points
├─────────────────────────────────────────────┤
│  Services        Orchestration, workflows   │  ← Coordinates layers
├─────────────────────────────────────────────┤
│  Engines         Pure business logic        │  ← No side effects
├─────────────────────────────────────────────┤
│  Integrations    DB repos, API clients      │  ← External world
├─────────────────────────────────────────────┤
│  Domain Models   Entities, value objects     │  ← Shared vocabulary
└─────────────────────────────────────────────┘
```

**Dependency rule:** each layer may only import from layers *below* it. Domain Models have zero internal dependencies.

```
delivery/
  http/
    order_handler.py          → imports services, delivery/schemas
  schemas/
    order_schemas.py          → imports domain_models
services/
  fulfillment_service.py      → imports engines, integrations, domain_models
engines/
  allocation_engine.py        → imports domain_models (pure functions)
integrations/
  database/repos/
    order_repo.py             → imports domain_models
  external_apis/
    payment_gateway.py        → imports domain_models
domain_models/
  order.py                    → imports nothing (or only other domain_models)
```

📖 Full rulesets: [`specification/references/rulesets.md`](specification/references/rulesets.md)

## Quick Start

### Using MASA with AI Agents

The [`specification/SKILL.md`](specification/SKILL.md) file is designed to be loaded as context for AI coding agents. It contains the complete framework rules, violation detection, and code generation patterns.

**With GitHub Copilot (custom instructions):**
```
Point your agent to specification/SKILL.md as a project-level instruction file.
```

**With any AI agent:**
```
Include the contents of specification/SKILL.md in your system prompt or project context.
```

### Starting a New MASA Project (Python)

```
src/
├── domain_models/          # Frozen dataclasses or Pydantic BaseModel
│   ├── __init__.py
│   └── order.py
├── engines/                # Pure functions, no I/O
│   ├── __init__.py
│   └── pricing_engine.py
├── services/               # Orchestration via dependency injection
│   ├── __init__.py
│   └── order_service.py
├── integrations/
│   ├── database/
│   │   └── repos/
│   │       └── order_repo.py
│   └── external_apis/
│       └── payment_gateway.py
└── delivery/
    ├── http/
    │   └── order_handler.py
    └── schemas/
        └── order_schemas.py
```

📖 Language-specific guides: [Python](specification/references/languages/python.md) · [JavaScript/TypeScript](specification/references/languages/javascript.md) · [Go](specification/references/languages/go.md)

## Experiments & Empirical Evidence

We evaluated MASA against DDD/Clean Architecture baselines using **three case studies** at increasing complexity, tested with multiple AI model tiers (small, mid, frontier).

### Cases

| Case | Domain | Files (MASA / Baseline) | Complexity |
|------|--------|------------------------|------------|
| **L** | Inventory API | ~15 / ~8 | Low |
| **M** | Task Management | ~30 / ~25 | Medium |
| **H** | Order Fulfillment | ~40 / ~30 | High |

### Key Results

**Composite Cognizability (C_core) by Model Tier:**

| Tier | MASA | Baseline | Δ | Lift | 95% CI |
|------|------|----------|---|------|--------|
| Frontier | 0.8272 | 0.7491 | +0.078 | +10.4% | [0.024, 0.140] |
| Mid | 0.7902 | 0.6786 | +0.112 | +16.4% | [0.033, 0.184] |
| Small | 0.7367 | 0.6239 | +0.113 | +18.1% | [0.023, 0.199] |

**Most robust finding:** In full-edit tasks, both architectures achieve 100% pass rate, but MASA produces **0 architectural violations** while baselines average **1–22 violations** per task.

📖 Full reproduction guide: [`experiments/README.md`](experiments/README.md)

## Repository Structure

```
masa-framework/
├── specification/             # Framework specification
│   ├── SKILL.md               # AI agent skill file (load as context)
│   └── references/
│       ├── pillars.md         # The Four Pillars deep dive
│       ├── rulesets.md        # Five Agentic Rulesets with examples
│       ├── validation.md      # Violation detection catalog
│       ├── task-execution-protocol.md
│       └── languages/         # Python, JavaScript, Go guides
├── experiments/
│   ├── cases/                 # Three case studies (L, M, H)
│   │   └── case-{l,m,h}/
│   │       ├── masa/          # MASA-compliant implementation
│   │       └── baseline/      # DDD/Clean Architecture baseline
│   ├── harness/               # Experiment runner infrastructure
│   └── results/               # Raw JSONL experimental data
├── metrics.md                 # Cognizability metrics definition
├── CONTRIBUTING.md
└── LICENSE                    # CC BY 4.0
```

## Contributing

Contributions, critiques, and empirical evaluations are welcome. Open a discussion, submit a pull request, or reach out directly.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

## License

This work is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
