

import uuid

from .base import (
    PaymentGateway,
    PaymentStartResult,
    PaymentVerificationResult,
)


class FakeGateway(PaymentGateway):

    def __init__(self):
        self._payments = {}

    def start_payment(
        self,
        *,
        order_id: int,
        amount_irr: int,
        callback_url: str,
    ) -> PaymentStartResult:

        authority = uuid.uuid4().hex

        self._payments[authority] = {
            "order_id": order_id,
            "amount_irr": amount_irr,
            "is_paid": False,
        }

        return PaymentStartResult(
            authority=authority,
            payment_url=(
                f"https://example.invalid/fake/{authority}"
            ),
        )

    def simulate_success(self, authority: str):
        payment = self._payments.get(authority)

        if payment is None:
            raise ValueError("تراکنش آزمایشی پیدا نشد.")

        payment["is_paid"] = True

    def verify_payment(
        self,
        *,
        authority: str,
        expected_amount_irr: int,
    ) -> PaymentVerificationResult:

        payment = self._payments.get(authority)

        if payment is None:
            return PaymentVerificationResult(
                verified=False,
            )

        if payment["amount_irr"] != expected_amount_irr:
            return PaymentVerificationResult(
                verified=False,
            )

        if not payment["is_paid"]:
            return PaymentVerificationResult(
                verified=False,
            )

        return PaymentVerificationResult(
            verified=True,
            reference=f"FAKE-REF-{authority}",
            amount_irr=payment["amount_irr"],
        )