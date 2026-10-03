from django.conf import settings
from django.db import models


class MuscleGroup(models.Model):
    name = models.CharField(
        "نام گروه عضلانی",
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        "شناسه",
        max_length=100,
        unique=True,
    )

    is_active = models.BooleanField(
        "فعال",
        default=True,
    )

    class Meta:
        verbose_name = "گروه عضلانی"
        verbose_name_plural = "گروه‌های عضلانی"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Exercise(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = "BEGINNER", "مبتدی"
        INTERMEDIATE = "INTERMEDIATE", "متوسط"
        ADVANCED = "ADVANCED", "پیشرفته"

    name = models.CharField(
        "نام حرکت",
        max_length=150,
        db_index=True,
    )

    description = models.TextField(
        "توضیحات حرکت",
        blank=True,
    )
    equipment = models.CharField(
        "تجهیزات موردنیاز",
        max_length=150,
        blank=True,
    )

    common_mistake = models.TextField(
        "اشتباه رایج",
        blank=True,
    )

    primary_muscle = models.ForeignKey(
        MuscleGroup,
        on_delete=models.PROTECT,
        related_name="primary_exercises",
        verbose_name="عضله اصلی",
    )

    secondary_muscles = models.ManyToManyField(
        MuscleGroup,
        related_name="secondary_exercises",
        verbose_name="عضلات فرعی",
        blank=True,
    )

    difficulty = models.CharField(
        "سطح حرکت",
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER,
    )

    is_system = models.BooleanField(
        "حرکت سیستمی",
        default=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_exercises",
        verbose_name="ایجادکننده",
        null=True,
        blank=True,
    )
    copied_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="copies",
        verbose_name="کپی شده از",
    )

    is_active = models.BooleanField(
        "فعال",
        default=True,
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
        verbose_name = "حرکت"
        verbose_name_plural = "حرکات"
        ordering = ("name",)

        indexes = [
            models.Index(
                fields=["is_system", "is_active"],
                name="exercise_system_active_idx",
            ),
        ]

    def __str__(self):
        return self.name


class ExerciseMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "عکس"
        VIDEO = "VIDEO", "ویدئو"
        GIF = "GIF", "گیف"

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="media",
        verbose_name="حرکت",
    )

    media_type = models.CharField(
        "نوع رسانه",
        max_length=10,
        choices=MediaType.choices,
    )

    file = models.FileField(
        "فایل",
        upload_to="exercises/media/",
    )

    thumbnail = models.ImageField(
        "تصویر پیش‌نمایش",
        upload_to="exercises/thumbnails/",
        blank=True,
        null=True,
    )

    is_primary = models.BooleanField(
        "رسانه اصلی",
        default=False,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
        default=0,
    )

    created_at = models.DateTimeField(
        "تاریخ ایجاد",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "رسانه حرکت"
        verbose_name_plural = "رسانه‌های حرکات"
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.exercise.name} - {self.get_media_type_display()}"