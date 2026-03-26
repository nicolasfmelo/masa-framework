from src.domain_models.order import Order
from src.domain_models.payment_authorization import PaymentRiskBand


def assess_payment_risk(order: Order) -> PaymentRiskBand:
    total_units = sum(line.quantity for line in order.line_items)
    if order.total_amount_cents >= 300000 or total_units >= 10:
        return "high"
    if order.total_amount_cents >= 120000 or len(order.line_items) >= 3:
        return "medium"
    return "low"
