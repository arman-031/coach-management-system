from datetime import timedelta

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from orders.models import PaymentAttempt


class Command(BaseCommand):

    help = "گزارش پرداخت‌های نامشخص نیازمند بررسی دستی"

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=15,
            help="حداقل عمر تلاش پرداخت به دقیقه",
        )

    def handle(self, *args, **options):

        minutes = options["minutes"]

        if minutes <= 0:
            raise CommandError("تعداد دقیقه باید بیشتر از صفر باشد.")

        cutoff = timezone.now() - timedelta(minutes=minutes)

        # Find all unresolved CREATED attempts,
        # regardless of the current order status.
        stale_attempts = (
            PaymentAttempt.objects.select_related("order")
            .filter(
                status=PaymentAttempt.Status.CREATED,
                created_at__lte=cutoff,
            )
            .order_by("created_at", "id")
        )

        count = stale_attempts.count()

        self.stdout.write(f"تعداد تلاش‌های نیازمند بررسی: {count}")

        for attempt in stale_attempts:

            has_authority = "YES" if attempt.gateway_authority else "NO"

            self.stdout.write(
                f"Attempt ID: {attempt.id} | "
                f"Order ID: {attempt.order_id} | "
                f"Order Status: {attempt.order.status} | "
                f"Provider: {attempt.provider} | "
                f"Has Authority: {has_authority} | "
                f"Tracking ID: {attempt.tracking_id}"
            )

        if count:
            self.stdout.write(
                self.style.WARNING(
                    "این پرداخت‌ها نیازمند بررسی هستند. "
                    "هیچ تراکنشی تأیید، رد یا حذف نشده است."
                )
            )
