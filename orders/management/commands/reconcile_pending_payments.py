

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.gateways.registry import get_active_gateway
from orders.models import PaymentAttempt, PurchaseOrder
from orders.reconciliation import reconcile_payment_attempt


class Command(BaseCommand):
    help = "بررسی کنترل‌شده پرداخت‌های در انتظار تأیید"

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=15,
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--execute",
            action="store_true",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]
        limit = options["limit"]
        execute = options["execute"]

        if minutes <= 0:
            raise CommandError(
                "تعداد دقیقه باید بیشتر از صفر باشد."
            )

        if not 1 <= limit <= 100:
            raise CommandError(
                "تعداد تراکنش‌ها باید بین 1 تا 100 باشد."
            )

        cutoff = timezone.now() - timedelta(
            minutes=minutes
        )

        # Select payments with an existing gateway authority.
        attempts = list(
            PaymentAttempt.objects.filter(
                status=PaymentAttempt.Status.PENDING,
                order__status=PurchaseOrder.Status.PENDING,
                created_at__lte=cutoff,
            )
            .exclude(gateway_authority__isnull=True)
            .exclude(gateway_authority="")
            .order_by("created_at", "id")[:limit]
        )

        self.stdout.write(
            f"تعداد تراکنش‌های انتخاب‌شده: {len(attempts)}"
        )

        if not execute:
            self.stdout.write(
                "حالت پیش‌نمایش: هیچ پرداختی تغییر نمی‌کند."
            )

            for attempt in attempts:
                self.stdout.write(
                    f"Attempt ID: {attempt.id} | "
                    f"Order ID: {attempt.order_id} | "
                    f"Provider: {attempt.provider}"
                )

            return

        # Real execution requires a trusted gateway.
        active_gateway = get_active_gateway()

        if active_gateway is None:
            raise CommandError(
                "هیچ درگاه پرداخت معتبری فعال نیست."
            )

        provider, gateway = active_gateway

        for attempt in attempts:

            # Never verify an attempt with another provider.
            if attempt.provider != provider:
                self.stdout.write(
                    self.style.WARNING(
                        f"Attempt {attempt.id}: SKIPPED_PROVIDER"
                    )
                )
                continue

            try:
                result = reconcile_payment_attempt(
                    attempt_id=attempt.id,
                    gateway=gateway,
                )

            except ValidationError:
                result = "MANUAL_REVIEW"

            self.stdout.write(
                f"Attempt {attempt.id}: {result}"
            )
