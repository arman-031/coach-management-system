

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from programs.models import Program
from questionnaires.services import initialize_program_questionnaire

from .models import PurchaseOrder


@transaction.atomic
def fulfill_verified_order(
    *,
    order_id,
    payment_reference,
    verified_amount_irr,
):
    """
    Fulfill an order AFTER trusted gateway verification.
    This function does not verify payment with a gateway.
    """

    # Check the payment information.
    if (
        not isinstance(payment_reference, str)
        or not payment_reference.strip()
        or len(payment_reference) > 150
    ):
        raise ValidationError(
            "شناسه تراکنش پرداخت معتبر نیست."
        )

    payment_reference = payment_reference.strip()

    if (
        type(verified_amount_irr) is not int
        or verified_amount_irr <= 0
    ):
        raise ValidationError(
            "مبلغ تأییدشده معتبر نیست."
        )

    # Lock the order to prevent duplicate fulfillment.
    order = PurchaseOrder.objects.select_for_update().get(
        pk=order_id,
    )

    # The paid amount must match the original order.
    if order.amount_irr != verified_amount_irr:
        raise ValidationError(
            "مبلغ پرداختی با مبلغ سفارش مطابقت ندارد."
        )

    # Idempotency: a repeated confirmation must not
    # create another program.
    if order.status == PurchaseOrder.Status.PAID:

        if (
            order.payment_reference == payment_reference
            and order.program_id is not None
        ):
            return order

        raise ValidationError(
            "این سفارش قبلاً با تراکنش دیگری ثبت شده است."
        )

    if order.status != PurchaseOrder.Status.PENDING:
        raise ValidationError(
            "این سفارش قابل تکمیل نیست."
        )

    # Reject a transaction reference used by another order.
    if PurchaseOrder.objects.filter(
        payment_reference=payment_reference,
    ).exclude(pk=order.pk).exists():
        raise ValidationError(
            "این تراکنش قبلاً برای سفارش دیگری ثبت شده است."
        )

    # Verify that the coach account is still valid.
    if (
        not order.coach.is_active
        or order.coach.role != User.Role.COACH
    ):
        raise ValidationError(
            "مربی سفارش معتبر یا فعال نیست."
        )

    # Create one new program for this purchase.
    program = Program.objects.create(
        student=order.student,
        program_type=order.program_type,
        created_by=order.coach,
    )

    # First purchase: create initial questionnaire.
    # Renewal: move the program to PREPARING.
    initialize_program_questionnaire(program.id)
    program.refresh_from_db()

    # Complete the purchase order.
    order.program = program
    order.status = PurchaseOrder.Status.PAID
    order.payment_reference = payment_reference
    order.paid_at = timezone.now()

    order.save(
        update_fields=[
            "program",
            "status",
            "payment_reference",
            "paid_at",
            "updated_at",
        ]
    )

    return order