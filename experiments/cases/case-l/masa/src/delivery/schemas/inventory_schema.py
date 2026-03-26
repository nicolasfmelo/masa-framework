from pydantic import BaseModel


class StockItemSchema(BaseModel):
    product_id: str
    product_name: str
    quantity: int


class AnomalySchema(BaseModel):
    product_id: str
    product_name: str
    message: str


class InventoryReportSchema(BaseModel):
    stock: list[StockItemSchema]
    low_stock: list[StockItemSchema]
    anomalies: list[AnomalySchema]
