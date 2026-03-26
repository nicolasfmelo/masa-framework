from fastapi import FastAPI

from src.delivery.http.order_fulfillment_handler import router, wire_services
from src.domain_models.ids import WarehouseId
from src.domain_models.inventory import WarehouseStock
from src.integrations.database.repos.fulfillment_attempt_repo import FulfillmentAttemptRepository
from src.integrations.database.repos.inventory_repo import InventoryRepository
from src.integrations.database.repos.order_repo import OrderRepository
from src.integrations.database.repos.payment_authorization_repo import PaymentAuthorizationRepository
from src.integrations.database.repos.shipment_repo import ShipmentRepository
from src.integrations.external_apis.payment_gateway import PaymentGateway
from src.integrations.external_apis.shipment_gateway import ShipmentGateway
from src.integrations.external_apis.warehouse_event_bus import WarehouseEventBus
from src.services.fulfillment_service import FulfillmentService
from src.services.order_intake_service import OrderIntakeService
from src.services.reconciliation_service import ReconciliationService

order_storage = {}
inventory_storage = {
    ("warehouse-north-1", "sku-1"): WarehouseStock(WarehouseId("warehouse-north-1"), "sku-1", "north", 10),
    ("warehouse-north-1", "sku-2"): WarehouseStock(WarehouseId("warehouse-north-1"), "sku-2", "north", 8),
    ("warehouse-south-1", "sku-1"): WarehouseStock(WarehouseId("warehouse-south-1"), "sku-1", "south", 5),
    ("warehouse-south-1", "sku-3"): WarehouseStock(WarehouseId("warehouse-south-1"), "sku-3", "south", 12),
    ("warehouse-west-1", "sku-2"): WarehouseStock(WarehouseId("warehouse-west-1"), "sku-2", "west", 4),
    ("warehouse-west-1", "sku-3"): WarehouseStock(WarehouseId("warehouse-west-1"), "sku-3", "west", 6),
}
payment_storage = {}
shipment_storage = {}
attempt_storage = {}
attempt_index = {}

order_repo = OrderRepository(order_storage)
inventory_repo = InventoryRepository(inventory_storage)
payment_repo = PaymentAuthorizationRepository(payment_storage)
shipment_repo = ShipmentRepository(shipment_storage)
attempt_repo = FulfillmentAttemptRepository(attempt_storage, attempt_index)
payment_gateway = PaymentGateway()
shipment_gateway = ShipmentGateway()
warehouse_event_bus = WarehouseEventBus()

order_intake_service = OrderIntakeService(order_repo=order_repo)
fulfillment_service = FulfillmentService(
    order_repo=order_repo,
    inventory_repo=inventory_repo,
    payment_repo=payment_repo,
    shipment_repo=shipment_repo,
    attempt_repo=attempt_repo,
    payment_gateway=payment_gateway,
    shipment_gateway=shipment_gateway,
    warehouse_event_bus=warehouse_event_bus,
)
reconciliation_service = ReconciliationService(
    order_repo=order_repo,
    payment_repo=payment_repo,
    shipment_repo=shipment_repo,
    attempt_repo=attempt_repo,
)

wire_services(
    order_intake_service=order_intake_service,
    fulfillment_service=fulfillment_service,
    reconciliation_service=reconciliation_service,
)

app = FastAPI(title="Order Fulfillment / Multi-Warehouse Service")
app.include_router(router)


def event_log() -> list[dict[str, str | int | None]]:
    return warehouse_event_bus.list_events()


def order_listing():
    return order_intake_service.list_orders()
