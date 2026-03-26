from fastapi import FastAPI

from src.application.use_cases.create_order import CreateOrderUseCase
from src.application.use_cases.fulfill_order import FulfillOrderUseCase
from src.application.use_cases.list_attempts import ListAttemptsUseCase
from src.application.use_cases.list_orders import ListOrdersUseCase
from src.application.use_cases.reconcile_order import ReconcileOrderUseCase
from src.application.use_cases.retry_fulfillment import RetryFulfillmentUseCase
from src.domain.entities.inventory import WarehouseStock
from src.infrastructure.gateways.in_memory_gateways import (
    InMemoryPaymentGateway,
    InMemoryShipmentGateway,
    InMemoryWarehouseEventPublisher,
)
from src.infrastructure.repositories.in_memory_repositories import (
    InMemoryFulfillmentAttemptRepository,
    InMemoryInventoryRepository,
    InMemoryOrderRepository,
    InMemoryPaymentAuthorizationRepository,
    InMemoryShipmentRepository,
)
from src.presentation.http.order_controller import router, wire_use_cases

order_storage = {}
inventory_storage = {
    ("warehouse-north-1", "sku-1"): WarehouseStock("warehouse-north-1", "sku-1", "north", 10),
    ("warehouse-north-1", "sku-2"): WarehouseStock("warehouse-north-1", "sku-2", "north", 8),
    ("warehouse-south-1", "sku-1"): WarehouseStock("warehouse-south-1", "sku-1", "south", 5),
    ("warehouse-south-1", "sku-3"): WarehouseStock("warehouse-south-1", "sku-3", "south", 12),
    ("warehouse-west-1", "sku-2"): WarehouseStock("warehouse-west-1", "sku-2", "west", 4),
    ("warehouse-west-1", "sku-3"): WarehouseStock("warehouse-west-1", "sku-3", "west", 6),
}
payment_storage = {}
shipment_storage = {}
attempt_storage = {}
attempt_index = {}

order_repository = InMemoryOrderRepository(order_storage)
inventory_repository = InMemoryInventoryRepository(inventory_storage)
payment_repository = InMemoryPaymentAuthorizationRepository(payment_storage)
shipment_repository = InMemoryShipmentRepository(shipment_storage)
attempt_repository = InMemoryFulfillmentAttemptRepository(attempt_storage, attempt_index)
payment_gateway = InMemoryPaymentGateway()
shipment_gateway = InMemoryShipmentGateway()
event_publisher = InMemoryWarehouseEventPublisher()

create_order_use_case = CreateOrderUseCase(order_repository)
list_orders_use_case = ListOrdersUseCase(order_repository)
fulfill_order_use_case = FulfillOrderUseCase(
    order_repository,
    inventory_repository,
    payment_repository,
    shipment_repository,
    attempt_repository,
    payment_gateway,
    shipment_gateway,
    event_publisher,
)
retry_fulfillment_use_case = RetryFulfillmentUseCase(order_repository, fulfill_order_use_case, attempt_repository)
reconcile_order_use_case = ReconcileOrderUseCase(order_repository, payment_repository, shipment_repository, attempt_repository)
list_attempts_use_case = ListAttemptsUseCase(order_repository, attempt_repository)

wire_use_cases(
    create_order_use_case=create_order_use_case,
    list_orders_use_case=list_orders_use_case,
    fulfill_order_use_case=fulfill_order_use_case,
    retry_fulfillment_use_case=retry_fulfillment_use_case,
    reconcile_order_use_case=reconcile_order_use_case,
    list_attempts_use_case=list_attempts_use_case,
)

app = FastAPI(title="Order Fulfillment / Multi-Warehouse Service")
app.include_router(router)


def event_log() -> list[dict[str, str | int | None]]:
    return event_publisher.list_events()


def order_listing():
    return list_orders_use_case.execute()
