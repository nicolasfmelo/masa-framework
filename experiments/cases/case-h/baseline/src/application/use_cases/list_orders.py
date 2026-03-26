from src.application.ports import OrderRepository
from src.domain.entities.order import Order


class ListOrdersUseCase:
    def __init__(self, order_repository: OrderRepository):
        self._order_repository = order_repository

    def execute(self) -> list[Order]:
        return self._order_repository.list_all()
