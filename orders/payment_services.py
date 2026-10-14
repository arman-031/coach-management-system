

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import PurchaseOrder, PaymentAttempt
from django.utils import timezone

from .services import fulfill_verified_order


def start_order_payment(
    *,
    order_id,
    gateway,
    provider,
    callback_url,
):
    # Find the order.
    order = PurchaseOrder.objects.get(
        pk=order_id,
    )

    # Only unpaid orders can start a payment.
    if order.status != PurchaseOrder.Status.PENDING:
        raise ValidationError(
            "این سفارش در وضعیت قابل پرداخت نیست."
        )

    # Ask the gateway to start a payment.
    payment_result = gateway.start_payment(
        order_id=order.id,
        amount_irr=order.amount_irr,
        callback_url=callback_url,
    )

    if (
        not payment_result.authority
        or not payment_result.payment_url
    ):
        raise ValidationError(
            "پاسخ درگاه پرداخت معتبر نیست."
        )

    # Save the payment attempt in PostgreSQL.
    with transaction.atomic():

        locked_order = (
            PurchaseOrder.objects
            .select_for_update()
            .get(pk=order_id)
        )

        if locked_order.status != PurchaseOrder.Status.PENDING:
            raise ValidationError(
                "وضعیت سفارش تغییر کرده است."
            )

        attempt = PaymentAttempt.objects.create(
            order=locked_order,
            provider=provider,
            amount_irr=locked_order.amount_irr,
            status=PaymentAttempt.Status.PENDING,
            gateway_authority=payment_result.authority,
        )

    return attempt, payment_result


def verify_order_payment(*, attempt_id, gateway):
    """
    Verify payment with a trusted gateway,
    then complete the order and payment attempt.
    """

    attempt = PaymentAttempt.objects.select_related(
        "order"
    ).get(pk=attempt_id)

    # An already verified attempt must not create another program.
    if attempt.status == PaymentAttempt.Status.VERIFIED:
        if (
            attempt.order.status == PurchaseOrder.Status.PAID
            and attempt.order.program_id is not None
            and attempt.gateway_reference
            == attempt.order.payment_reference
        ):
            return attempt

        raise ValidationError(
            "اطلاعات تراکنش تأییدشده ناسازگار است."
        )

    if (
        attempt.status != PaymentAttempt.Status.PENDING
        or not attempt.gateway_authority
    ):
        raise ValidationError(
            "این تلاش پرداخت قابل تأیید نیست."
        )

    # Ask the trusted gateway to verify this payment.
    verification = gateway.verify_payment(
        authority=attempt.gateway_authority,
        expected_amount_irr=attempt.amount_irr,
    )

    if not verification.verified:
        raise ValidationError(
            "پرداخت هنوز تأیید نشده است."
        )

    # Validate the verified transaction details.
    if (
        not isinstance(verification.reference, str)
        or not verification.reference.strip()
        or len(verification.reference) > 150
        or type(verification.amount_irr) is not int
        or verification.amount_irr != attempt.amount_irr
    ):
        raise ValidationError(
            "اطلاعات پرداخت تأییدشده معتبر نیست."
        )

    reference = verification.reference.strip()

    # Complete all database changes together.
    with transaction.atomic():

        order = PurchaseOrder.objects.select_for_update().get(
            pk=attempt.order_id
        )

        locked_attempt = (
            PaymentAttempt.objects.select_for_update()
            .get(pk=attempt_id)
        )

        # Handle concurrent repeated verification.
        if locked_attempt.status == PaymentAttempt.Status.VERIFIED:
            if (
                order.status == PurchaseOrder.Status.PAID
                and order.program_id is not None
                and locked_attempt.gateway_reference
                == order.payment_reference
            ):
                return locked_attempt

            raise ValidationError(
                "اطلاعات تراکنش تأییدشده ناسازگار است."
            )

        if (
            locked_attempt.status != PaymentAttempt.Status.PENDING
            or locked_attempt.gateway_authority
            != attempt.gateway_authority
            or locked_attempt.amount_irr != attempt.amount_irr
        ):
            raise ValidationError(
                "وضعیت تلاش پرداخت تغییر کرده است."
            )

        if order.status != PurchaseOrder.Status.PENDING:
            raise ValidationError(
                "این سفارش قبلاً تکمیل شده یا قابل پرداخت نیست."
            )

        # Reuse the order fulfillment service.
        fulfill_verified_order(
            order_id=order.id,
            payment_reference=reference,
            verified_amount_irr=verification.amount_irr,
        )

        locked_attempt.status = PaymentAttempt.Status.VERIFIED
        locked_attempt.gateway_reference = reference
        locked_attempt.verified_at = timezone.now()

        locked_attempt.save(
            update_fields=[
                "status",
                "gateway_reference",
                "verified_at",
                "updated_at",
            ]
        )

        return locked_attempt