import jdatetime
from exercises.serializers import ExerciseMediaSerializer
from django.utils import timezone
from rest_framework import serializers
from exercises.models import Exercise
from .models import Program,ProgramDay,ProgramExercise


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


class ProgramDayCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramDay

        fields = (
            "id",
            "program",
            "title",
            "note",
            "order",
            "created_at",
        )

        read_only_fields = (
            "id",
            "program",
            "created_at",
        )


class ProgramExerciseCreateSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(
        source="exercise.name",
        read_only=True,
    )

    exercise = serializers.PrimaryKeyRelatedField(
        queryset=Exercise.objects.filter(is_active=True),
        error_messages={
            "does_not_exist": "حرکت انتخاب‌شده وجود ندارد یا فعال نیست.",
            "incorrect_type": "شناسه حرکت معتبر نیست.",
        },
    )

    class Meta:
        model = ProgramExercise

        fields = (
            "id",
            "program_day",
            "exercise",
            "exercise_name",
            "sets",
            "reps",
            "rest_seconds",
            "weight",
            "note",
            "order",
        )

        read_only_fields = (
            "id",
            "program_day",
            "exercise_name",
        )

    def validate_exercise(self, exercise):
        user = self.context["request"].user

        if not (
            exercise.is_system
            or exercise.created_by_id == user.id
        ):
            raise serializers.ValidationError(
                "اجازه استفاده از این حرکت را ندارید."
            )

        return exercise

    def validate_sets(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "تعداد ست باید حداقل یک باشد."
            )

        return value


class ProgramExerciseReadSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(
        source="exercise.name",
        read_only=True,
    )

    exercise_description = serializers.CharField(
        source="exercise.description",
        read_only=True,
    )

    exercise_media = ExerciseMediaSerializer(
        source="exercise.media",
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProgramExercise

        fields = (
            "id",
            "exercise",
            "exercise_name",
            "exercise_description",
            "exercise_media",
            "sets",
            "reps",
            "rest_seconds",
            "weight",
            "note",
            "order",
        )

        read_only_fields = fields


class ProgramDayListSerializer(serializers.ModelSerializer):
    exercises = ProgramExerciseReadSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProgramDay

        fields = (
            "id",
            "program",
            "title",
            "note",
            "order",
            "exercises",
        )

        read_only_fields = fields