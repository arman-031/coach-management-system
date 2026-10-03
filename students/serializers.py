from rest_framework import serializers
from accounts.models import User
from .models import StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    gender_display = serializers.CharField(
        source="get_gender_display",
        read_only=True,
    )

    referral_source_display = serializers.CharField(
        source="get_referral_source_display",
        read_only=True,
    )

    class Meta:
        model = StudentProfile

        fields = (
            "birth_date",
            "gender",
            "gender_display",
            "height",
            "weight",
            "referral_source",
            "referral_source_display",
            "referral_description",
            "updated_at",
        )

        read_only_fields = (
            "gender_display",
            "referral_source_display",
            "updated_at",
        )



class StudentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "created_at",
        )

        read_only_fields = fields


class StudentDetailSerializer(serializers.ModelSerializer):
    profile = StudentProfileSerializer(
        source="student_profile",
        read_only=True,
    )

    class Meta:
        model = User

        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "created_at",
            "profile",
        )

        read_only_fields = fields


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
        )