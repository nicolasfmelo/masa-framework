from dataclasses import replace

from src.domain_models.order import Order
from src.integrations.database.repos.order_repo import OrderRepository


class OrderIntakeService:
    def __init__(self, order_repo: OrderRepository):
        self._order_repo = order_repo

    def create_order(self, order: Order) -> Order:
        accepted_order = replace(order, status="accepted", failure_reason=None)
        return self._order_repo.save(accepted_order)

    def list_orders(self) -> list[Order]:
        return self._order_repo.list_all()
