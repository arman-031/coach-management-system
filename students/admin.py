from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "height",
        "weight",
        "referral_source",
        "created_at",
    )

    search_fields = (
        "user__phone",
        "user__first_name",
        "user__last_name",
    )

    list_filter = (
        "gender",
        "referral_source",
    )