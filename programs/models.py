from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.core.validators import MinValueValidator



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




# ---------------------------------------
# Nutrition Day
# ---------------------------------------

class NutritionDay(models.Model):

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="nutrition_days",
        limit_choices_to={
            "program_type": Program.ProgramType.NUTRITION
        },
        verbose_name="برنامه تغذیه",
    )

    title = models.CharField(
        "عنوان روز یا الگو",
        max_length=150,
    )

    note = models.TextField(
        "توضیحات",
        blank=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
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
        verbose_name = "روز برنامه تغذیه"
        verbose_name_plural = "روزهای برنامه تغذیه"

        ordering = ("order", "id")

        indexes = [
            models.Index(
                fields=["program", "order"],
                name="nutrition_day_order_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.program_id
            and self.program.program_type
            != Program.ProgramType.NUTRITION
        ):
            raise ValidationError({
                "program": (
                    "روز تغذیه فقط می‌تواند متعلق "
                    "به برنامه تغذیه باشد."
                )
            })

    def __str__(self):
        return f"{self.program_id} - {self.title}"



    # ---------------------------------------
# Nutrition Meal
# ---------------------------------------

class NutritionMeal(models.Model):

    nutrition_day = models.ForeignKey(
        NutritionDay,
        on_delete=models.CASCADE,
        related_name="meals",
        verbose_name="روز تغذیه",
    )

    title = models.CharField(
        "عنوان وعده",
        max_length=120,
    )

    meal_time = models.TimeField(
        "زمان وعده",
        null=True,
        blank=True,
    )

    note = models.TextField(
        "توضیحات مربی",
        blank=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
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
        verbose_name = "وعده غذایی"
        verbose_name_plural = "وعده‌های غذایی"

        ordering = ("order", "id")

        indexes = [
            models.Index(
                fields=["nutrition_day", "order"],
                name="nutrition_meal_order_idx",
            ),
        ]

    def __str__(self):
        return f"{self.nutrition_day.title} - {self.title}"



# ---------------------------------------
# Nutrition Food Item
# ---------------------------------------

class NutritionFoodItem(models.Model):

    class Unit(models.TextChoices):
        GRAM = "GRAM", "گرم"
        MILLILITER = "MILLILITER", "میلی‌لیتر"
        PIECE = "PIECE", "عدد"
        CUP = "CUP", "لیوان"
        TABLESPOON = "TABLESPOON", "قاشق غذاخوری"
        TEASPOON = "TEASPOON", "قاشق چای‌خوری"
        SLICE = "SLICE", "برش"
        PALM = "PALM", "کف دست"
        BOWL = "BOWL", "کاسه"

    nutrition_meal = models.ForeignKey(
        NutritionMeal,
        on_delete=models.CASCADE,
        related_name="food_items",
        verbose_name="وعده غذایی",
    )

    name = models.CharField(
        "نام ماده غذایی",
        max_length=150,
    )

    quantity = models.DecimalField(
        "مقدار مصرف",
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    unit = models.CharField(
        "واحد اندازه‌گیری",
        max_length=20,
        choices=Unit.choices,
    )

    note = models.TextField(
        "توضیحات مربی",
        blank=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
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
        verbose_name = "ماده غذایی برنامه"
        verbose_name_plural = "مواد غذایی برنامه"

        ordering = ("order", "id")

        indexes = [
            models.Index(
                fields=["nutrition_meal", "order"],
                name="nutrition_food_order_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.quantity} "
            f"{self.get_unit_display()}"
        )