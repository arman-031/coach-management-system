from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        COACH = "COACH", "مربی"
        STUDENT = "STUDENT", "شاگرد"

    username = None

    phone_validator = RegexValidator(
        regex=r"^\+?\d{10,15}$",
        message="شماره موبایل واردشده معتبر نیست.",
    )

    phone = models.CharField(
        "شماره موبایل",
        max_length=16,
        unique=True,
        validators=[phone_validator],
        error_messages={
            "unique": "کاربری با این شماره موبایل قبلاً ثبت‌نام کرده است.",
        },
    )

    role = models.CharField(
        "نقش کاربر",
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    created_at = models.DateTimeField(
        "تاریخ عضویت",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "آخرین بروزرسانی",
        auto_now=True,
    )

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.phone