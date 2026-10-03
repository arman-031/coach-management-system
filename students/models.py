

from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "MALE", "مرد"
        FEMALE = "FEMALE", "زن"

    class ReferralSource(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", "اینستاگرام"
        GOOGLE = "GOOGLE", "گوگل"
        FRIEND = "FRIEND", "معرفی دوستان"
        TELEGRAM = "TELEGRAM", "تلگرام"
        OTHER = "OTHER", "سایر"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name="کاربر",
    )

    birth_date = models.DateField(
        "تاریخ تولد",
        null=True,
        blank=True,
    )

    gender = models.CharField(
        "جنسیت",
        max_length=10,
        choices=Gender.choices,
        blank=True,
    )

    height = models.PositiveSmallIntegerField(
        "قد",
        null=True,
        blank=True,
        help_text="قد بر حسب سانتی‌متر",
    )

    weight = models.DecimalField(
        "وزن",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="وزن بر حسب کیلوگرم",
    )

    referral_source = models.CharField(
        "نحوه آشنایی با مربی",
        max_length=20,
        choices=ReferralSource.choices,
        blank=True,
    )

    referral_description = models.CharField(
        "توضیح نحوه آشنایی",
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        "تاریخ ایجاد",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "آخرین بروزرسانی",
        auto_now=True,
    )

    class Meta:
        verbose_name = "پروفایل شاگرد"
        verbose_name_plural = "پروفایل شاگردان"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.phone