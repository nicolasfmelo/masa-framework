from src.domain_models.exceptions import PaymentDeclinedError
from src.domain_models.ids import PaymentAuthorizationId
from src.domain_models.order import Order
from src.domain_models.payment_authorization import PaymentAuthorization, PaymentRiskBand


class PaymentGateway:
    def authorize_payment(self, order: Order, risk_band: PaymentRiskBand) -> PaymentAuthorization:
        status = "authorized"
        if "decline" in order.payment_token or (risk_band == "high" and order.region == "fraud-zone"):
            status = "declined"
        gateway_reference = f"gateway-{order.id.value[-6:]}-{risk_band}"
        authorization = PaymentAuthorization(
            id=PaymentAuthorizationId.new(),
            order_id=order.id,
            amount_cents=order.total_amount_cents,
            risk_band=risk_band,
            status=status,
            gateway_reference=gateway_reference,
        )
        if authorization.status == "declined":
            return authorization
        return authorization
