# Task Management + Scheduling API

Case M implementation following the **Modular Agentic Semantic Architecture (MASA)**.

## Scope

This medium-complexity case covers:

- task creation
- task listing
- task updates
- task assignment
- task scheduling
- notification policy validation

## How to run

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 3001
```

## Structure

```text
src/
├── domain_models/
├── engines/
├── integrations/
├── services/
└── delivery/
```
