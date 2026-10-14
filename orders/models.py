

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from programs.models import Program

import uuid


class PurchaseOrder(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "در انتظار پرداخت"
        PAID = "PAID", "پرداخت‌شده"
        FAILED = "FAILED", "پرداخت ناموفق"
        CANCELED = "CANCELED", "لغوشده"

    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name="شاگرد",
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_orders",
        verbose_name="مربی",
    )

    program_type = models.CharField(
        "نوع برنامه",
        max_length=20,
        choices=Program.ProgramType.choices,
    )

    amount_irr = models.PositiveBigIntegerField(
        "مبلغ به ریال",
        validators=[MinValueValidator(1)],
    )

    status = models.CharField(
        "وضعیت سفارش",
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    program = models.OneToOneField(
        "programs.Program",
        on_delete=models.PROTECT,
        related_name="purchase_order",
        null=True,
        blank=True,
        verbose_name="برنامه ایجادشده",
    )

    payment_reference = models.CharField(
        "شناسه تراکنش پرداخت",
        max_length=150,
        unique=True,
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        "زمان تأیید پرداخت",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "تاریخ ایجاد سفارش",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "آخرین بروزرسانی",
        auto_now=True,
    )

    class Meta:
        verbose_name = "سفارش خرید"
        verbose_name_plural = "سفارش‌های خرید"
        ordering = ("-created_at",)

    def __str__(self):
        return (
            f"سفارش {self.pk} - "
            f"{self.get_program_type_display()} - "
            f"{self.get_status_display()}"
        )


class PaymentAttempt(models.Model):

    class Status(models.TextChoices):
        CREATED = "CREATED", "ایجادشده"
        PENDING = "PENDING", "در انتظار پرداخت"
        VERIFIED = "VERIFIED", "تأییدشده"
        FAILED = "FAILED", "ناموفق"

    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
        verbose_name="سفارش",
    )

    tracking_id = models.UUIDField(
        "شناسه پیگیری داخلی",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    provider = models.CharField(
        "درگاه پرداخت",
        max_length=40,
    )

    amount_irr = models.PositiveBigIntegerField(
        "مبلغ پرداخت به ریال",
        validators=[MinValueValidator(1)],
    )

    status = models.CharField(
        "وضعیت تلاش پرداخت",
        max_length=15,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )

    gateway_authority = models.CharField(
        "شناسه درخواست درگاه",
        max_length=150,
        null=True,
        blank=True,
    )

    gateway_reference = models.CharField(
        "شناسه تراکنش درگاه",
        max_length=150,
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        "زمان تأیید",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "تلاش پرداخت"
        verbose_name_plural = "تلاش‌های پرداخت"
        ordering = ("-created_at",)

        constraints = [
            models.UniqueConstraint(
                fields=["provider", "gateway_authority"],
                name="unique_provider_authority",
            ),
            models.UniqueConstraint(
                fields=["provider", "gateway_reference"],
                name="unique_provider_reference",
            ),
        ]

    def __str__(self):
        return f"پرداخت {self.pk} - سفارش {self.order_id}"