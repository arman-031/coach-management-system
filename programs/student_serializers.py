from rest_framework import serializers

from .models import Program
from .serializers import (
    ProgramDayListSerializer,
    to_jalali_datetime,
)


# ---------------------------------------
# Student Program List
# ---------------------------------------

class StudentProgramListSerializer(
    serializers.ModelSerializer
):
    published_at_jalali = serializers.SerializerMethodField()
    expires_at_jalali = serializers.SerializerMethodField()

    class Meta:
        model = Program

        fields = (
            "id",
            "program_type",
            "status",
            "duration_days",
            "published_at",
            "published_at_jalali",
            "expires_at",
            "expires_at_jalali",
        )

    def get_published_at_jalali(self, obj):
        return to_jalali_datetime(obj.published_at)

    def get_expires_at_jalali(self, obj):
        return to_jalali_datetime(obj.expires_at)


# ---------------------------------------
# Student Program Detail
# ---------------------------------------

class StudentProgramDetailSerializer(
    StudentProgramListSerializer
):
    days = ProgramDayListSerializer(
        many=True,
        read_only=True,
    )

    class Meta(StudentProgramListSerializer.Meta):
        fields = (
            *StudentProgramListSerializer.Meta.fields,
            "days",
        )