from django.conf import settings
from django.db import models


class Program(models.Model):
    class ProgramType(models.TextChoices):
        BODYBUILDING = "BODYBUILDING", "بدنسازی"
        NUTRITION = "NUTRITION", "تغذیه"
        CORRECTIVE = "CORRECTIVE", "اصلاحی"

    class Status(models.TextChoices):
        WAITING = "WAITING", "در انتظار"
        PREPARING = "PREPARING", "در حال آماده‌سازی"
        ACTIVE = "ACTIVE", "فعال"
        EXPIRED = "EXPIRED", "منقضی شده"

    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.PROTECT,
        related_name="programs",
        verbose_name="شاگرد",
    )

    program_type = models.CharField(
        "نوع برنامه",
        max_length=20,
        choices=ProgramType.choices,
    )

    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
    )

    duration_days = models.PositiveSmallIntegerField(
        "مدت برنامه به روز",
        default=45,
    )

    published_at = models.DateTimeField(
        "تاریخ انتشار",
        null=True,
        blank=True,
    )

    expires_at = models.DateTimeField(
        "تاریخ پایان",
        null=True,
        blank=True,
    )

    is_deleted = models.BooleanField(
        "حذف شده",
        default=False,
        db_index=True,
    )

    deleted_at = models.DateTimeField(
        "تاریخ حذف",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_programs",
        verbose_name="ایجادکننده",
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
        verbose_name = "برنامه"
        verbose_name_plural = "برنامه‌ها"
        ordering = ("-created_at",)

        indexes = [
            models.Index(
                fields=["student", "status"],
                name="program_student_status_idx",
            ),
            models.Index(
                fields=["program_type", "status"],
                name="program_type_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.get_program_type_display()} - "
            f"{self.get_status_display()}"
        )


class ProgramDay(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="days",
        verbose_name="برنامه",
    )

    title = models.CharField(
        "عنوان جلسه",
        max_length=150,
    )

    note = models.TextField(
        "توضیحات جلسه",
        blank=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب جلسه",
        default=1,
    )

    is_deleted = models.BooleanField(
        "حذف شده",
        default=False,
        db_index=True,
    )

    deleted_at = models.DateTimeField(
        "تاریخ حذف",
        null=True,
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
        verbose_name = "جلسه برنامه"
        verbose_name_plural = "جلسات برنامه"
        ordering = (
            "order",
            "id",
        )

        indexes = [
            models.Index(
                fields=["program", "order"],
                name="program_day_order_idx",
            ),
        ]

    def __str__(self):
        return f"{self.program} - {self.title}"


class ProgramExercise(models.Model):
    program_day = models.ForeignKey(
        ProgramDay,
        on_delete=models.CASCADE,
        related_name="exercises",
        verbose_name="جلسه",
    )

    exercise = models.ForeignKey(
        "exercises.Exercise",
        on_delete=models.PROTECT,
        related_name="program_exercises",
        verbose_name="حرکت",
    )

    sets = models.PositiveSmallIntegerField(
        "تعداد ست",
        default=3,
    )

    reps = models.CharField(
        "تکرار",
        max_length=50,
    )

    rest_seconds = models.PositiveSmallIntegerField(
        "استراحت بین ست‌ها به ثانیه",
        null=True,
        blank=True,
    )

    weight = models.CharField(
        "وزنه یا شدت",
        max_length=100,
        blank=True,
    )

    note = models.TextField(
        "توضیحات مربی",
        blank=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب حرکت",
        default=1,
    )

    is_deleted = models.BooleanField(
        "حذف شده",
        default=False,
        db_index=True,
    )

    deleted_at = models.DateTimeField(
        "تاریخ حذف",
        null=True,
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
        verbose_name = "حرکت برنامه"
        verbose_name_plural = "حرکات برنامه"
        ordering = (
            "order",
            "id",
        )

        indexes = [
            models.Index(
                fields=["program_day", "order"],
                name="program_exercise_order_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.program_day.title} - "
            f"{self.exercise.name}"
        )