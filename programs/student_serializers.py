from rest_framework import serializers

from .models import Program
from questionnaires.models import ProgramQuestionnaire
from .serializers import (
    ProgramDayListSerializer,
    to_jalali_datetime,
)

from .nutrition_serializers import (
    NutritionDayReadSerializer,
)

# ---------------------------------------
# Student Program List
# ---------------------------------------


class StudentProgramListSerializer(serializers.ModelSerializer):

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    questionnaire_status = serializers.CharField(
        source="questionnaire.status",
        read_only=True,
        allow_null=True,
    )

    questionnaire_status_display = serializers.CharField(
        source="questionnaire.get_status_display",
        read_only=True,
        allow_null=True,
    )

    student_message = serializers.SerializerMethodField()

    published_at_jalali = serializers.SerializerMethodField()
    expires_at_jalali = serializers.SerializerMethodField()

    class Meta:
        model = Program

        fields = (
            "id",
            "program_type",
            "status",
            "status_display",
            "questionnaire_status",
            "questionnaire_status_display",
            "student_message",
            "duration_days",
            "published_at",
            "published_at_jalali",
            "expires_at",
            "expires_at_jalali",
        )

        read_only_fields = fields

    def get_student_message(self, obj):

        # Published program.
        if obj.status == Program.Status.ACTIVE:
            return "برنامه شما آماده و قابل مشاهده است."

        # Expired program remains available in archive.
        if obj.status == Program.Status.EXPIRED:
            return "دوره این برنامه پایان یافته و " "در آرشیو قابل مشاهده است."

        # A questionnaire might not exist on renewals.
        questionnaire = getattr(
            obj,
            "questionnaire",
            None,
        )

        if questionnaire is not None:

            # Coach asked the student to revise answers.
            if questionnaire.status == (ProgramQuestionnaire.Status.REVISION_REQUESTED):
                return "لطفاً پاسخ‌های پرسش‌نامه را " "اصلاح و دوباره ارسال کنید."

            # Student has not submitted the questionnaire.
            if questionnaire.status in (
                ProgramQuestionnaire.Status.NOT_STARTED,
                ProgramQuestionnaire.Status.DRAFT,
            ):
                return "لطفاً پرسش‌نامه برنامه را " "تکمیل و ارسال کنید."

        # Coach is preparing the program.
        if obj.status == Program.Status.PREPARING:
            return "مربی در حال آماده‌سازی برنامه شماست."

        # Default waiting message.
        return "برنامه شما در انتظار بررسی مربی است."

    def get_published_at_jalali(self, obj):
        return to_jalali_datetime(obj.published_at)

    def get_expires_at_jalali(self, obj):
        return to_jalali_datetime(obj.expires_at)


# ---------------------------------------
# Student Program Detail
# ---------------------------------------


class StudentProgramDetailSerializer(StudentProgramListSerializer):

    # Bodybuilding and corrective sessions
    days = ProgramDayListSerializer(
        many=True,
        read_only=True,
    )

    # Nutrition days, meals and food items
    nutrition_days = NutritionDayReadSerializer(
        many=True,
        read_only=True,
    )

    class Meta(StudentProgramListSerializer.Meta):

        fields = (
            *StudentProgramListSerializer.Meta.fields,
            "days",
            "nutrition_days",
        )

        read_only_fields = fields
