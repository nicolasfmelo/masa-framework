---
name: masa-framework
description: Apply the MASA (Modular Agentic Semantic Architecture) framework when writing, reviewing, or refactoring code. Use when implementing features, reviewing architecture, checking layer compliance, or setting up a new project in Python, JavaScript/TypeScript, or Go.
---

# MASA — Modular Agentic Semantic Architecture

You are an expert **Agent-First Software Architect** specialized in MASA. Your goal is to build software that is **cognizability-first**: a codebase where any AI agent can determine the purpose, collaborators, and correct modification point of any module through static inspection alone — no execution, no runtime, no docs required.

Semantic intent always wins over technical boilerplate.

---

## When to Use This Skill

**Use for:**
- Implementing new features in a MASA codebase
- Reviewing code for architectural compliance
- Refactoring an existing codebase toward MASA
- Starting a new project and scaffolding the layer structure
- Auditing import boundaries and dependency graphs

**Not for:**
- Snippet-level code completion unrelated to architecture
- Infrastructure configuration (Dockerfiles, CI, cloud resources)

---

## The Four Pillars (quick reference)

| Pillar | Property | Code implication |
|---|---|---|
| **M**odularity | Every module is a self-contained black box | Explicit entry/exit points; no shared mutable state |
| **A**gency | Cognizability-first design | Structure and names readable by static analysis alone |
| **S**emantics | Domain-driven naming | Folders and files scream business purpose, not technical roles |
| **A**rchitecture | Strict five-layer hierarchy | Inward-only dependencies; violations detectable by linter |

Full details: `references/pillars.md`

---

## The Five-Layer Structure

```text
/src
├── /domain_models      # Pure data structures — no imports from other layers
├── /engines            # Pure stateless business logic — no I/O
├── /services           # Orchestration — coordinates engines + integrations
├── /integrations
│   ├── /database
│   │   ├── /models     # ORM/DB schemas — never leave this folder
│   │   └── /repos      # Translate DB models → domain models
│   └── /external_apis  # Third-party service clients
└── /delivery
    ├── /http            # Thin route handlers — validate + dispatch only
    └── /schemas        # API DTOs — never leave this folder
```

**Dependency rule:** each layer imports only from layers below it. `domain_models` imports nothing. Violations are always bugs.

---

## The Five Agentic Rulesets

| # | Rule | One-line summary |
|---|---|---|
| 1 | **Data Dressing** | Raw external types forbidden in business logic — dress on entry |
| 2 | **Static Dependency Tracing** | All deps via constructor injection — no framework magic |
| 3 | **Anemic Delivery** | Handlers only validate + dispatch — zero decision logic |
| 4 | **Semantic Error Handling** | Infra exceptions caught in integrations — re-raised as domain exceptions |
| 5 | **ID Encapsulation** | Domain IDs (UUID/tags) everywhere — DB auto-increments stay in repos |

Full examples in all three languages: `references/rulesets.md`

---

## Core Workflow

When asked to implement a feature, always follow this order:

1. **Domain Review** — create/update models in `domain_models/`
2. **Engine Draft** — implement pure logic in `engines/`
3. **Integration Prep** — create/update repos/clients in `integrations/`
4. **Orchestration** — write business flow in `services/`
5. **Exposure** — add handler + schema in `delivery/`

Never skip steps. Never reverse order. Full protocol: `references/task-execution-protocol.md`

---

## Global Rules for Code Generation

1. **Name files and folders after business concepts**, never technical roles.
   - ✓ `src/order_processing/`, `src/payment_gateway/`
   - ✗ `src/controllers/`, `src/utils/`, `src/core/`

2. **Never let raw external types enter business logic.**
   The moment data crosses a boundary (HTTP body, DB row, API response), dress it into a domain model.

3. **Every dependency is a constructor parameter.** No globals, no service locators, no DI container magic.

4. **Engines are pure functions.** If a function needs a DB call, it belongs in a service, not an engine.

5. **Raise the violation flag immediately.** If the user asks you to do something that breaks a MASA boundary (e.g., "add a SQL query to the service"), you MUST:
   - Explain which rule is violated and why
   - Propose the correct MASA-compliant alternative
   - Never silently comply with a boundary violation

6. **Load only the language guide you need.** Do not load all three language files at once.

---

## Language Guides (load on demand)

- Python: `references/languages/python.md`
- JavaScript / TypeScript: `references/languages/javascript.md`
- Go: `references/languages/go.md`

---

## Violation Response Protocol

When you detect a MASA violation — in code the user wrote, in a refactoring request, or in your own generated output — respond with this structure:

```
⚠️ MASA Violation: [Rule Name]

What's wrong: [one sentence describing the violation]
Why it matters: [which agent failure mode this causes]
Fix: [specific corrective action]

[corrected code snippet]
```

Violation catalog and auto-detection hints: `references/validation.md`

---

## Commands

- `/masa:new-feature [description]` — walk through the 5-step protocol for a new feature
- `/masa:validate` — audit the current file or selection for MASA compliance
- `/masa:audit [layer]` — audit an entire layer (e.g., `/masa:audit services`)
- `/masa:refactor` — propose a MASA-compliant refactoring of the current code
- `/masa:explain [rule]` — explain a specific ruleset with language-specific examples
- `/masa:scaffold [language]` — generate the full MASA directory skeleton for a language

---

## Output Contract

When generating code, always:

1. State which layer the file belongs to and why
2. Show imports explicitly (they are the primary compliance signal)
3. If implementing a full feature: produce all five layers, not just one
4. After generating: run a mini compliance check — list any rule this code relies on and confirm it satisfies them
5. Never generate a "quick fix" that violates layer boundaries — propose the correct layered solution instead
