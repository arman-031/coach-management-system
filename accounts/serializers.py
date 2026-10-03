

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from students.models import StudentProfile
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        error_messages={
            "required": "رمز عبور الزامی است.",
            "blank": "رمز عبور نمی‌تواند خالی باشد.",
        },
    )

    password_confirm = serializers.CharField(
        write_only=True,
        error_messages={
            "required": "تکرار رمز عبور الزامی است.",
            "blank": "تکرار رمز عبور نمی‌تواند خالی باشد.",
        },
    )

    class Meta:
        model = User

        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "email",
            "password",
            "password_confirm",
        )

        read_only_fields = ("id",)

        extra_kwargs = {
            "first_name": {
                "required": True,
                "allow_blank": False,
                "error_messages": {
                    "required": "نام الزامی است.",
                    "blank": "نام نمی‌تواند خالی باشد.",
                },
            },
            "last_name": {
                "required": True,
                "allow_blank": False,
                "error_messages": {
                    "required": "نام خانوادگی الزامی است.",
                    "blank": "نام خانوادگی نمی‌تواند خالی باشد.",
                },
            },
            "email": {
                "required": False,
            },
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {
                    "password_confirm": "رمز عبور و تکرار آن یکسان نیستند."
                }
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            role=User.Role.STUDENT,
            **validated_data,
        )

        StudentProfile.objects.create(user=user)

        return user


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(
        source="get_role_display",
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
            "role",
            "role_display",
            "created_at",
        )

        read_only_fields = (
            "id",
            "phone",
            "role",
            "role_display",
            "created_at",
        )