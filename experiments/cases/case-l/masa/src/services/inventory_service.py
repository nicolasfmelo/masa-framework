from src.domain_models.inventory import InventoryReport
from src.engines.inventory_engine import calculate_inventory
from src.integrations.csv_parser import parse_csv


class InventoryService:
    def __init__(self, csv_parser=parse_csv, engine=calculate_inventory):
        self._parse_csv = csv_parser
        self._calculate_inventory = engine

    def analyze(self, file_content: str) -> InventoryReport:
        movements = self._parse_csv(file_content)
        return self._calculate_inventory(movements)
