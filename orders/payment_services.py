
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .gateways.base import GatewayStartRejected
from .models import PurchaseOrder, PaymentAttempt
from .services import fulfill_verified_order


class PaymentNotConfirmed(ValidationError):
    """Payment was not confirmed by the gateway."""
    pass

def start_order_payment(
    *,
    order_id,
    gateway,
    provider,
    callback_url,
):
    """
    Start payment and prevent duplicate active attempts.

    A confirmed gateway rejection marks the attempt FAILED.
    An unknown error leaves it CREATED for later review.
    """

    # Step 1: Reserve a payment attempt.
    with transaction.atomic():

        order = (
            PurchaseOrder.objects
            .select_for_update()
            .get(pk=order_id)
        )

        if order.status != PurchaseOrder.Status.PENDING:
            raise ValidationError(
                "این سفارش در وضعیت قابل پرداخت نیست."
            )

        active_attempt_exists = PaymentAttempt.objects.filter(
            order=order,
            status__in=[
                PaymentAttempt.Status.CREATED,
                PaymentAttempt.Status.PENDING,
            ],
        ).exists()

        if active_attempt_exists:
            raise ValidationError(
                "یک تلاش پرداخت فعال برای این سفارش وجود دارد."
            )

        attempt = PaymentAttempt.objects.create(
            order=order,
            provider=provider,
            amount_irr=order.amount_irr,
            status=PaymentAttempt.Status.CREATED,
        )

    # Step 2: Contact the gateway outside DB transaction.
    try:
        payment_result = gateway.start_payment(
            order_id=order.id,
            amount_irr=order.amount_irr,
            callback_url=callback_url,
        )

        if (
            not isinstance(payment_result.authority, str)
            or not payment_result.authority.strip()
            or len(payment_result.authority) > 150
            or not isinstance(payment_result.payment_url, str)
            or not payment_result.payment_url.strip()
        ):
            raise ValidationError(
                "پاسخ درگاه پرداخت معتبر نیست."
            )

    except GatewayStartRejected:
        # The gateway explicitly rejected the request.
        PaymentAttempt.objects.filter(
            pk=attempt.id,
            status=PaymentAttempt.Status.CREATED,
        ).update(
            status=PaymentAttempt.Status.FAILED,
            updated_at=timezone.now(),
        )

        # Re-raise ONLY inside the except block.
        raise

    # Other errors, including timeouts, leave the attempt
    # in CREATED so it can be reviewed safely.

    # Step 3: Save the gateway response.
    with transaction.atomic():

        locked_order = (
            PurchaseOrder.objects
            .select_for_update()
            .get(pk=order_id)
        )

        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .get(pk=attempt.id)
        )

        if locked_order.status != PurchaseOrder.Status.PENDING:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
            order_is_pending = False

        else:
            attempt.gateway_authority = (
                payment_result.authority.strip()
            )

            attempt.status = PaymentAttempt.Status.PENDING

            attempt.save(
                update_fields=[
                    "gateway_authority",
                    "status",
                    "updated_at",
                ]
            )

            order_is_pending = True

    if not order_is_pending:
        raise ValidationError(
            "وضعیت سفارش هنگام شروع پرداخت تغییر کرده است."
        )

    return attempt, payment_result


def verify_order_payment(*, attempt_id, gateway):
    """
    Verify payment through a trusted gateway,
    then complete the order atomically.
    """

    attempt = PaymentAttempt.objects.select_related(
        "order"
    ).get(pk=attempt_id)

    # Prevent duplicate program creation.
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

    # Step 1: Verify with the gateway.
    verification = gateway.verify_payment(
        authority=attempt.gateway_authority,
        expected_amount_irr=attempt.amount_irr,
    )

    if not verification.verified:
        raise PaymentNotConfirmed(
            "پرداخت هنوز تأیید نشده است."
        )

    # Step 2: Validate the verified payment.
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

    # Step 3: Complete database changes atomically.
    with transaction.atomic():

        order = (
            PurchaseOrder.objects
            .select_for_update()
            .get(pk=attempt.order_id)
        )

        locked_attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .get(pk=attempt_id)
        )

        # Handle repeated verification safely.
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

        # Create the student's program.
        fulfill_verified_order(
            order_id=order.id,
            payment_reference=reference,
            verified_amount_irr=verification.amount_irr,
        )

        # Mark the payment attempt as verified.
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
