

from django.contrib import admin

from .models import (
    QuestionnaireTemplate,
    TemplateQuestion,
)

from .forms import TemplateQuestionAdminForm


# ---------------------------------------
# Questionnaire Template Admin
# ---------------------------------------

@admin.register(QuestionnaireTemplate)
class QuestionnaireTemplateAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "program_type",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "program_type",
        "is_active",
    )

    search_fields = (
        "title",
        "description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------
# Template Question Admin
# ---------------------------------------

@admin.register(TemplateQuestion)
class TemplateQuestionAdmin(admin.ModelAdmin):

    form = TemplateQuestionAdminForm

    list_display = (
        "id",
        "text",
        "template",
        "answer_type",
        "is_required",
        "order",
        "is_active",
    )

    list_filter = (
        "template",
        "answer_type",
        "is_required",
        "is_active",
    )

    search_fields = (
        "text",
        "template__title",
    )

    list_select_related = (
        "template",
    )

    ordering = (
        "template",
        "order",
        "id",
    )

    fields = (
        "template",
        "text",
        "answer_type",
        "options_text",
        "is_required",
        "order",
        "is_active",
    )

    def has_delete_permission(self, request, obj=None):
        return False