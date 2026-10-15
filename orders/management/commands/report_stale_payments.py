


from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import PaymentAttempt, PurchaseOrder


class Command(BaseCommand):
    help = "گزارش تلاش‌های پرداخت نیمه‌تمام"

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=15,
            help="حداقل مدت انتظار به دقیقه",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]

        if minutes <= 0:
            raise CommandError(
                "تعداد دقیقه باید بیشتر از صفر باشد."
            )

        cutoff = timezone.now() - timedelta(
            minutes=minutes
        )

        stale_attempts = PaymentAttempt.objects.filter(
            status=PaymentAttempt.Status.CREATED,
            order__status=PurchaseOrder.Status.PENDING,
            created_at__lte=cutoff,
        ).order_by(
            "created_at",
            "id",
        )

        count = stale_attempts.count()

        self.stdout.write(
            f"تعداد تلاش‌های نیازمند بررسی: {count}"
        )

        for attempt in stale_attempts:
            self.stdout.write(
                f"Attempt ID: {attempt.id} | "
                f"Order ID: {attempt.order_id} | "
                f"Status: {attempt.status}"
            )

        if count:
            self.stdout.write(
                self.style.WARNING(
                    "این تلاش‌ها فقط گزارش شدند؛ "
                    "هیچ وضعیت پرداختی تغییر نکرد."
                )
            )
