from fastapi import APIRouter, HTTPException, UploadFile, File

from src.delivery.schemas.inventory_schema import AnomalySchema, InventoryReportSchema, StockItemSchema
from src.domain_models.exceptions import InvalidCSVError
from src.domain_models.inventory import InventoryReport
from src.services.inventory_service import InventoryService

router = APIRouter()
_service = InventoryService()


def _to_schema(report: InventoryReport) -> InventoryReportSchema:
    return InventoryReportSchema(
        stock=[StockItemSchema(**vars(item)) for item in report.stock],
        low_stock=[StockItemSchema(**vars(item)) for item in report.low_stock],
        anomalies=[AnomalySchema(**vars(item)) for item in report.anomalies],
    )


@router.post("/analyze-inventory", response_model=InventoryReportSchema)
async def analyze_inventory(file: UploadFile = File(...)) -> InventoryReportSchema:
    raw_bytes = await file.read()

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")

    try:
        report = _service.analyze(content)
    except InvalidCSVError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _to_schema(report)
