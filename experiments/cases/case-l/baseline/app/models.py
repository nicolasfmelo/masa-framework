# Flat model definitions.
# R5: product_id is a raw str primitive — no encapsulation.
# Mixed with constants that arguably belong in the logic layer.

LOW_STOCK_THRESHOLD = 10


class StockItem:
    def __init__(self, product_id: str, product_name: str, quantity: int):
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity


class Anomaly:
    def __init__(self, product_id: str, product_name: str, message: str):
        self.product_id = product_id
        self.product_name = product_name
        self.message = message
