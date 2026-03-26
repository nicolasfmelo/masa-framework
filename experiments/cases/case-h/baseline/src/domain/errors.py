class OrderNotFoundError(Exception):
    pass


class InventoryUnavailableError(Exception):
    pass


class PaymentDeclinedError(Exception):
    pass


class ShipmentPlanningError(Exception):
    pass


class DuplicateFulfillmentAttemptError(Exception):
    pass
