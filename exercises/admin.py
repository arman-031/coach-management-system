from django.contrib import admin

from .models import (
    Exercise,
    ExerciseMedia,
    MuscleGroup,
)


class ExerciseMediaInline(admin.TabularInline):
    model = ExerciseMedia
    extra = 0

    fields = (
        "media_type",
        "file",
        "thumbnail",
        "is_primary",
        "order",
    )

    ordering = (
        "order",
        "id",
    )


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )

    list_filter = (
        "is_active",
    )

    ordering = (
        "name",
    )


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "primary_muscle",
        "difficulty",
        "is_system",
        "is_active",
        "created_by",
    )

    list_filter = (
        "is_system",
        "is_active",
        "difficulty",
        "primary_muscle",
    )

    search_fields = (
        "name",
        "description",
        "equipment",
        "primary_muscle__name",
    )

    ordering = (
        "name",
    )

    filter_horizontal = (
        "secondary_muscles",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        ExerciseMediaInline,
    ]


@admin.register(ExerciseMedia)
class ExerciseMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "exercise",
        "media_type",
        "is_primary",
        "order",
        "created_at",
    )

    list_filter = (
        "media_type",
        "is_primary",
    )

    search_fields = (
        "exercise__name",
    )

    ordering = (
        "exercise",
        "order",
        "id",
    )

    readonly_fields = (
        "created_at",
    )