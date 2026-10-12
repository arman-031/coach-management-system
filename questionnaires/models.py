

import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from programs.models import Program


# ---------------------------------------
# Questionnaire Template
# ---------------------------------------

class QuestionnaireTemplate(models.Model):

    program_type = models.CharField(
        "نوع برنامه",
        max_length=20,
        choices=Program.ProgramType.choices,
        unique=True,
    )

    title = models.CharField(
        "عنوان پرسش‌نامه",
        max_length=150,
    )

    description = models.TextField(
        "توضیحات",
        blank=True,
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
        verbose_name = "قالب پرسش‌نامه"
        verbose_name_plural = "قالب‌های پرسش‌نامه"
        ordering = ("program_type",)

    def __str__(self):
        return self.title


# ---------------------------------------
# Template Question
# ---------------------------------------

class TemplateQuestion(models.Model):

    class AnswerType(models.TextChoices):
        SHORT_TEXT = "SHORT_TEXT", "متن کوتاه"
        LONG_TEXT = "LONG_TEXT", "متن بلند"
        NUMBER = "NUMBER", "عددی"
        YES_NO = "YES_NO", "بله یا خیر"
        SINGLE_CHOICE = "SINGLE_CHOICE", "تک‌انتخابی"
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "چندانتخابی"

    template = models.ForeignKey(
        QuestionnaireTemplate,
        on_delete=models.PROTECT,
        related_name="questions",
        verbose_name="قالب پرسش‌نامه",
    )

    key = models.UUIDField(
        "شناسه داخلی سؤال",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    text = models.CharField(
        "متن سؤال",
        max_length=300,
    )

    answer_type = models.CharField(
        "نوع پاسخ",
        max_length=20,
        choices=AnswerType.choices,
        default=AnswerType.SHORT_TEXT,
    )

    options = models.JSONField(
        "گزینه‌های پاسخ",
        default=list,
        blank=True,
    )

    is_required = models.BooleanField(
        "پاسخ اجباری است",
        default=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
        default=1,
        validators=[MinValueValidator(1)],
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
        verbose_name = "سؤال قالب"
        verbose_name_plural = "سؤالات قالب"

        ordering = ("order", "id")

        indexes = [
            models.Index(
                fields=["template", "is_active", "order"],
                name="qq_question_lookup_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if not isinstance(self.options, list):
            raise ValidationError({
                "options": "گزینه‌ها باید به‌صورت لیست باشند."
            })

        choice_types = (
            self.AnswerType.SINGLE_CHOICE,
            self.AnswerType.MULTIPLE_CHOICE,
        )

        if self.answer_type in choice_types:

            if len(self.options) < 2:
                raise ValidationError({
                    "options": (
                        "سؤال انتخابی باید حداقل "
                        "دو گزینه داشته باشد."
                    )
                })

            seen_values = set()

            for option in self.options:

                if not isinstance(option, dict):
                    raise ValidationError({
                        "options": "ساختار گزینه نامعتبر است."
                    })

                value = option.get("value")
                label = option.get("label")

                if (
                    not isinstance(value, str)
                    or not value.strip()
                    or not isinstance(label, str)
                    or not label.strip()
                ):
                    raise ValidationError({
                        "options": (
                            "هر گزینه باید کد و "
                            "عنوان معتبر داشته باشد."
                        )
                    })

                if value in seen_values:
                    raise ValidationError({
                        "options": "کد گزینه‌ها نباید تکراری باشد."
                    })

                seen_values.add(value)

        elif self.options:
            raise ValidationError({
                "options": (
                    "فقط سؤال‌های انتخابی "
                    "می‌توانند گزینه داشته باشند."
                )
            })

    def __str__(self):
        return self.text



# ---------------------------------------
# Program Questionnaire
# ---------------------------------------

class ProgramQuestionnaire(models.Model):

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "شروع نشده"
        DRAFT = "DRAFT", "پیش‌نویس"
        SUBMITTED = "SUBMITTED", "ارسال نهایی"
        REVISION_REQUESTED = (
            "REVISION_REQUESTED",
            "درخواست اصلاح",
        )

    class AssignmentType(models.TextChoices):
        INITIAL = "INITIAL", "پرسش‌نامه اولیه"
        COACH_REQUEST = (
            "COACH_REQUEST",
            "درخواست مربی",
        )

    program = models.OneToOneField(
        Program,
        on_delete=models.CASCADE,
        related_name="questionnaire",
        verbose_name="برنامه شاگرد",
    )

    template = models.ForeignKey(
        QuestionnaireTemplate,
        on_delete=models.PROTECT,
        related_name="program_questionnaires",
        verbose_name="قالب اصلی",
    )

    assignment_type = models.CharField(
        "دلیل ایجاد",
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.INITIAL,
    )

    status = models.CharField(
        "وضعیت پرسش‌نامه",
        max_length=25,
        choices=Status.choices,
        default=Status.NOT_STARTED,
        db_index=True,
    )

    revision_reason = models.TextField(
        "دلیل درخواست اصلاح",
        blank=True,
    )

    submitted_at = models.DateTimeField(
        "زمان ارسال نهایی",
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
        verbose_name = "پرسش‌نامه برنامه"
        verbose_name_plural = "پرسش‌نامه‌های برنامه"

    def clean(self):
        super().clean()

        if self.program_id and self.template_id:
            if (
                self.program.program_type
                != self.template.program_type
            ):
                raise ValidationError({
                    "template": (
                        "نوع قالب پرسش‌نامه باید "
                        "با نوع برنامه یکسان باشد."
                    )
                })

    def __str__(self):
        return f"پرسش‌نامه برنامه {self.program_id}"


# ---------------------------------------
# Program Questionnaire Item
# ---------------------------------------

class ProgramQuestionnaireItem(models.Model):

    questionnaire = models.ForeignKey(
        ProgramQuestionnaire,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="پرسش‌نامه",
    )

    source_question = models.ForeignKey(
        TemplateQuestion,
        on_delete=models.PROTECT,
        related_name="program_items",
        verbose_name="سؤال اصلی",
    )

    question_key = models.UUIDField(
        "شناسه سؤال",
    )

    text = models.CharField(
        "متن سؤال در زمان ایجاد",
        max_length=300,
    )

    answer_type = models.CharField(
        "نوع پاسخ",
        max_length=20,
        choices=TemplateQuestion.AnswerType.choices,
    )

    options = models.JSONField(
        "گزینه‌های سؤال",
        default=list,
        blank=True,
    )

    is_required = models.BooleanField(
        "پاسخ اجباری",
        default=True,
    )

    order = models.PositiveSmallIntegerField(
        "ترتیب نمایش",
        default=1,
        validators=[MinValueValidator(1)],
    )

    answer = models.JSONField(
        "پاسخ شاگرد",
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
        verbose_name = "سؤال و پاسخ برنامه"
        verbose_name_plural = "سؤالات و پاسخ‌های برنامه"

        ordering = ("order", "id")

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "questionnaire",
                    "question_key",
                ],
                name="unique_program_question_key",
            ),
        ]

        indexes = [
            models.Index(
                fields=["questionnaire", "order"],
                name="pq_item_order_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.questionnaire_id and self.source_question_id:
            if (
                self.source_question.template_id
                != self.questionnaire.template_id
            ):
                raise ValidationError({
                    "source_question": (
                        "سؤال باید متعلق به قالب "
                        "همین پرسش‌نامه باشد."
                    )
                })

    def __str__(self):
        return self.text