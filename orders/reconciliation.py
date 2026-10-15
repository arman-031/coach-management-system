

from .models import PaymentAttempt
from .payment_services import (
    PaymentNotConfirmed,
    verify_order_payment,
)


def reconcile_payment_attempt(*, attempt_id, gateway):
    """
    Recheck a payment using a trusted gateway.

    Return a result without assuming an
    unconfirmed payment has failed.
    """

    attempt = PaymentAttempt.objects.get(
        pk=attempt_id
    )

    # No confirmed gateway authority is available.
    if (
        attempt.status == PaymentAttempt.Status.CREATED
        or not attempt.gateway_authority
    ):
        return "MANUAL_REVIEW"

    # Failed attempts cannot be recovered here.
    if attempt.status == PaymentAttempt.Status.FAILED:
        return "NOT_APPLICABLE"

    # Already verified: check consistency without
    # creating another program.
    if attempt.status == PaymentAttempt.Status.VERIFIED:
        verify_order_payment(
            attempt_id=attempt.id,
            gateway=gateway,
        )
        return "VERIFIED"

    # Only pending attempts can be rechecked.
    if attempt.status != PaymentAttempt.Status.PENDING:
        return "MANUAL_REVIEW"

    try:
        verify_order_payment(
            attempt_id=attempt.id,
            gateway=gateway,
        )

    except PaymentNotConfirmed:
        return "NOT_CONFIRMED"

    except (TimeoutError, ConnectionError):
        return "RETRY_LATER"

    return "VERIFIED"