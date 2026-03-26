from src.domain_models.ids import OrderId
from src.domain_models.payment_authorization import PaymentAuthorization


class PaymentAuthorizationRepository:
    def __init__(self, storage: dict[str, PaymentAuthorization]):
        self._storage = storage

    def save(self, authorization: PaymentAuthorization) -> PaymentAuthorization:
        self._storage[authorization.id.value] = authorization
        return authorization

    def list_by_order(self, order_id: OrderId) -> list[PaymentAuthorization]:
        return [item for item in self._storage.values() if item.order_id.value == order_id.value]
