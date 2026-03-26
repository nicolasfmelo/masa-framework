# Reproducing MASA Experiments

This directory contains everything needed to replicate the cognizability experiments described in the MASA framework evaluation.

## Overview

The experiments compare **MASA-compliant** codebases against **baseline** (DDD/Clean Architecture) implementations across three complexity tiers, measuring how well AI agents can navigate and modify each codebase.

### Experiment Cases

| Case | Complexity | Domain | Description |
|------|-----------|--------|-------------|
| **Case L** | Low | Inventory API | Simple CRUD + analysis over CSV-backed inventory |
| **Case M** | Medium | Task Management | Task CRUD, assignment, scheduling, notifications |
| **Case H** | High | Order Fulfillment | Multi-warehouse allocation, payments, shipments, reconciliation |

Each case has two variants:
- `masa/` — MASA-compliant 5-layer architecture
- `baseline/` — DDD / Clean Architecture equivalent

### Two Experimental Conditions

1. **Structure-Only (C1)** — Given a task description and directory tree, can the agent identify the correct files and dependency edges?
2. **Full-Edit (C2)** — Given a task description and full codebase, can the agent produce a correct patch that passes tests *and* preserves architecture?

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS account with [Amazon Bedrock](https://aws.amazon.com/bedrock/) access (Claude models)

## Setup

```bash
cd experiments/harness
uv sync
```

Configure your AWS credentials. The harness uses the `codeboost` AWS CLI profile by default:

```bash
aws configure --profile codeboost
```

## Running Experiments

### Structure-Only Condition (C1)

```bash
# Case L — MASA variant, frontier model
uv run python run_experiment.py \
  --catalog tasks/case-l/catalog.json \
  --condition structure-only \
  --architecture masa-full \
  --codebase-root ../cases/case-l/masa \
  --model-tier frontier \
  --results-path ../results/case-l-structure.jsonl

# Case L — Baseline variant
uv run python run_experiment.py \
  --catalog tasks/case-l/catalog.json \
  --condition structure-only \
  --architecture baseline \
  --codebase-root ../cases/case-l/baseline \
  --model-tier frontier \
  --results-path ../results/case-l-baseline-structure.jsonl
```

### Full-Edit Condition (C2)

```bash
# Case M — MASA variant, mid-tier model
uv run python run_experiment.py \
  --catalog tasks/case-m/catalog.json \
  --condition full-edit \
  --architecture masa-full \
  --codebase-root ../cases/case-m/masa \
  --model-tier mid \
  --results-path ../results/case-m-edit.jsonl
```

### Available Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `--catalog` | `tasks/case-{l,m,h}/catalog.json` | Task definitions for each case |
| `--condition` | `structure-only`, `full-edit` | Experiment condition |
| `--architecture` | `masa-full`, `baseline` | Which codebase variant to test |
| `--codebase-root` | Path to case directory | Root of the codebase under test |
| `--model-tier` | `small`, `mid`, `frontier` | Model capability tier |
| `--model-id` | Bedrock model ID | Override specific model (optional) |
| `--task-id` | e.g. `L-r01 L-r02` | Run specific tasks only (optional) |
| `--results-path` | Output file path | Where to write JSONL results |
| `--max-tokens` | Integer | Max output tokens (default: model-dependent) |
| `--temperature` | Float | Sampling temperature (default: 0.0) |

## Analyzing Results

```bash
# Cross-case analysis
uv run python analyze_results.py \
  --results ../results/full-structure.jsonl ../results/full-edit.jsonl

# Per-case analysis
uv run python analyze_case_results.py \
  --results ../results/case-m-full-edit.jsonl ../results/case-m-full-structure.jsonl
```

## Key Metrics

| Metric | Condition | Description |
|--------|-----------|-------------|
| **Retrieval F1** | C1 | Did the agent find the correct files? |
| **Graph F1** | C1 | Did the agent reconstruct the correct dependency edges? |
| **Compliance Score** | C1 | Did the agent respect architectural layer rules? |
| **C_core** | C1 | Composite: mean(Retrieval, Graph, Compliance) |
| **Pass Rate** | C2 | Does the generated patch pass tests? |
| **Violation Count** | C2 | Number of MASA/architecture rule violations in the patch |
| **Token Usage** | Both | Input + output tokens consumed |

See [`metrics.md`](../metrics.md) for formal definitions.

## Results

Raw experimental data is in `results/`. Each `.jsonl` file contains one JSON object per experimental run with all metrics, model info, and token counts.

Summary statistics are in the `.json` files.

## Task Catalogs

Each case has a `catalog.json` in `harness/tasks/case-{l,m,h}/` containing 24 tasks across four blocks:

- **Retrieval** — File identification tasks
- **Graph Reconstruction** — Dependency tracing tasks
- **Patch** — Code modification tasks
- **Failure Path** — Error handling and edge case tasks

Tasks span three difficulty levels (low, medium, high) and include ground truth for both MASA and baseline variants.
