# Inventory Analysis API

A warehouse inventory movement API built in Python following the **Modular Agentic Semantic Architecture (MASA)**.

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --host 0.0.0.0 --port 3000
```

## Usage

```bash
curl -X POST http://localhost:3000/analyze-inventory \
  -F "file=@inventory.csv"
```

Interactive docs available at: http://localhost:3000/docs

## Project Structure

```
src/
├── domain_models/     # Pure data contracts (StockMovement, StockItem, Anomaly, InventoryReport)
├── engines/           # Stateless pure logic (calculate_inventory)
├── services/          # Orchestration (InventoryService)
├── integrations/      # CSV parsing (parse_csv)
└── delivery/
    ├── http/          # FastAPI route handlers
    └── schemas/       # Pydantic request/response schemas
```
