import jdatetime

from django.utils import timezone
from rest_framework import serializers

from .models import Program


def to_jalali_datetime(value):
    if not value:
        return None

    local_datetime = timezone.localtime(value)

    jalali_datetime = jdatetime.datetime.fromgregorian(
        datetime=local_datetime,
    )

    return jalali_datetime.strftime(
        "%Y/%m/%d - %H:%M"
    )


class ProgramListSerializer(serializers.ModelSerializer):
    student_phone = serializers.CharField(
        source="student.user.phone",
        read_only=True,
    )

    program_type_display = serializers.CharField(
        source="get_program_type_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    published_at_jalali = serializers.SerializerMethodField()
    expires_at_jalali = serializers.SerializerMethodField()

    class Meta:
        model = Program

        fields = (
            "id",
            "student",
            "student_phone",
            "program_type",
            "program_type_display",
            "status",
            "status_display",
            "duration_days",
            "published_at",
            "published_at_jalali",
            "expires_at",
            "expires_at_jalali",
            "created_at",
        )

        read_only_fields = fields

    def get_published_at_jalali(self, obj):
        return to_jalali_datetime(
            obj.published_at,
        )

    def get_expires_at_jalali(self, obj):
        return to_jalali_datetime(
            obj.expires_at,
        )


class ProgramDetailSerializer(serializers.ModelSerializer):
    student_phone = serializers.CharField(
        source="student.user.phone",
        read_only=True,
    )

    program_type_display = serializers.CharField(
        source="get_program_type_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    created_by_phone = serializers.CharField(
        source="created_by.phone",
        read_only=True,
    )

    published_at_jalali = serializers.SerializerMethodField()
    expires_at_jalali = serializers.SerializerMethodField()

    class Meta:
        model = Program

        fields = (
            "id",
            "student",
            "student_phone",
            "program_type",
            "program_type_display",
            "status",
            "status_display",
            "duration_days",
            "published_at",
            "published_at_jalali",
            "expires_at",
            "expires_at_jalali",
            "created_by",
            "created_by_phone",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_published_at_jalali(self, obj):
        return to_jalali_datetime(
            obj.published_at,
        )

    def get_expires_at_jalali(self, obj):
        return to_jalali_datetime(
            obj.expires_at,
        )


class ProgramCreateSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    program_type_display = serializers.CharField(
        source="get_program_type_display",
        read_only=True,
    )

    class Meta:
        model = Program

        fields = (
            "id",
            "student",
            "program_type",
            "program_type_display",
            "status",
            "status_display",
            "duration_days",
            "published_at",
            "expires_at",
        )

        read_only_fields = (
            "id",
            "program_type_display",
            "status",
            "status_display",
            "duration_days",
            "published_at",
            "expires_at",
        )