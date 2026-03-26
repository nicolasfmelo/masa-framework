from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.service import process_data  # R2: static import

router = APIRouter()


# R3: response schema defined inside delivery layer — but also, the handler
#     itself decodes bytes, catches a raw ValueError (infra exception) and
#     does inline dict→schema mapping, mixing protocol concerns with dispatch.

class StockItemOut(BaseModel):
    product_id: str
    product_name: str
    quantity: int


class AnomalyOut(BaseModel):
    product_id: str
    product_name: str
    message: str


class InventoryReportOut(BaseModel):
    stock: list[StockItemOut]
    low_stock: list[StockItemOut]
    anomalies: list[AnomalyOut]


@router.post("/analyze-inventory", response_model=InventoryReportOut)
async def handle_file(file: UploadFile = File(...)) -> InventoryReportOut:
    # R3: byte decoding and error branching happening inside the handler
    raw_bytes = await file.read()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")

    # R4: catching raw ValueError (infra/parsing error) at delivery layer
    try:
        result = process_data(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return InventoryReportOut(
        stock=[StockItemOut(**item) for item in result["stock"]],
        low_stock=[StockItemOut(**item) for item in result["low_stock"]],
        anomalies=[AnomalyOut(**item) for item in result["anomalies"]],
    )
