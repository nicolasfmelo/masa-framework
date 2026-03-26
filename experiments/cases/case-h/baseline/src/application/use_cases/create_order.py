from dataclasses import replace

from src.application.ports import OrderRepository
from src.domain.entities.order import Order


class CreateOrderUseCase:
    def __init__(self, order_repository: OrderRepository):
        self._order_repository = order_repository

    def execute(self, order: Order) -> Order:
        accepted_order = replace(order, status="accepted", failure_reason=None)
        return self._order_repository.save(accepted_order)
