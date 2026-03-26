# Order Fulfillment / Multi-Warehouse Service

Case H implementation following the **Modular Agentic Semantic Architecture (MASA)**.

## Scope

This high-complexity case covers:

- order creation with multiple line items
- multi-warehouse allocation
- payment authorization
- shipment creation
- fulfillment retries with idempotency
- reconciliation of inconsistent states
- warehouse event publication

## How to run

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 3002
```
