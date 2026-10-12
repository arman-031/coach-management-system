

from rest_framework import serializers
import math
from .models import (
    ProgramQuestionnaire,
    ProgramQuestionnaireItem,
)


class ProgramQuestionnaireItemSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProgramQuestionnaireItem

        fields = (
            "id",
            "text",
            "answer_type",
            "options",
            "is_required",
            "order",
            "answer",
        )

        read_only_fields = fields


class StudentQuestionnaireSerializer(
    serializers.ModelSerializer
):
    items = ProgramQuestionnaireItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProgramQuestionnaire

        fields = (
            "id",
            "assignment_type",
            "status",
            "revision_reason",
            "submitted_at",
            "items",
        )

        read_only_fields = fields


class QuestionnaireAnswerUpdateSerializer(
    serializers.Serializer
):
    answer = serializers.JSONField(
        allow_null=True,
    )

    def validate_answer(self, value):
        item = self.context["item"]
        answer_type = item.answer_type

        # Null means clearing the draft answer.
        if value is None:
            return None

        if answer_type in ("SHORT_TEXT", "LONG_TEXT"):
            if not isinstance(value, str):
                raise serializers.ValidationError(
                    "پاسخ باید متنی باشد."
                )

            value = value.strip()

            max_length = (
                250 if answer_type == "SHORT_TEXT"
                else 5000
            )

            if len(value) > max_length:
                raise serializers.ValidationError(
                    f"پاسخ نباید بیشتر از {max_length} کاراکتر باشد."
                )

            return value or None

        if answer_type == "NUMBER":
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise serializers.ValidationError(
                    "پاسخ باید یک عدد معتبر باشد."
                )

            return value

        if answer_type == "YES_NO":
            if not isinstance(value, bool):
                raise serializers.ValidationError(
                    "پاسخ باید true یا false باشد."
                )

            return value

        allowed_values = {
            option["value"]
            for option in item.options
        }

        if answer_type == "SINGLE_CHOICE":
            if (
                not isinstance(value, str)
                or value not in allowed_values
            ):
                raise serializers.ValidationError(
                    "گزینه انتخاب‌شده معتبر نیست."
                )

            return value

        if answer_type == "MULTIPLE_CHOICE":
            if not isinstance(value, list):
                raise serializers.ValidationError(
                    "پاسخ باید لیستی از گزینه‌ها باشد."
                )

            if not all(
                isinstance(option, str)
                for option in value
            ):
                raise serializers.ValidationError(
                    "کد گزینه‌ها باید متنی باشد."
                )

            if len(value) != len(set(value)):
                raise serializers.ValidationError(
                    "گزینه تکراری مجاز نیست."
                )

            if not set(value).issubset(allowed_values):
                raise serializers.ValidationError(
                    "یک یا چند گزینه نامعتبر هستند."
                )

            return value or None

        raise serializers.ValidationError(
            "نوع سؤال پشتیبانی نمی‌شود."
        )


class CoachRevisionRequestSerializer(
    serializers.Serializer
):
    reason = serializers.CharField(
        min_length=5,
        max_length=1000,
        trim_whitespace=True,
        error_messages={
            "required": "دلیل درخواست اصلاح الزامی است.",
            "blank": "دلیل درخواست اصلاح نمی‌تواند خالی باشد.",
            "min_length": "دلیل اصلاح باید حداقل ۵ کاراکتر باشد.",
            "max_length": "دلیل اصلاح نباید بیشتر از ۱۰۰۰ کاراکتر باشد.",
        },
    )