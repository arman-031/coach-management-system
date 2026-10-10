from django.contrib import admin

from .models import (
    Program,
    ProgramDay,
    ProgramExercise,
    NutritionDay,
    NutritionMeal,
    NutritionFoodItem
)


class ProgramDayInline(admin.TabularInline):
    model = ProgramDay
    extra = 0
    show_change_link = True

    fields = (
        "title",
        "order",
        "note",
    )

    ordering = (
        "order",
        "id",
    )


class ProgramExerciseInline(admin.TabularInline):
    model = ProgramExercise
    extra = 0

    autocomplete_fields = (
        "exercise",
    )

    fields = (
        "exercise",
        "sets",
        "reps",
        "rest_seconds",
        "weight",
        "order",
        "note",
    )

    ordering = (
        "order",
        "id",
    )


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "program_type",
        "status",
        "duration_days",
        "published_at",
        "expires_at",
        "created_by",
        "created_at",
    )

    list_filter = (
        "program_type",
        "status",
        "created_at",
    )

    search_fields = (
        "student__user__phone",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        ProgramDayInline,
    ]


@admin.register(ProgramDay)
class ProgramDayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program",
        "title",
        "order",
        "created_at",
    )

    search_fields = (
        "title",
        "program__student__user__phone",
    )

    ordering = (
        "program",
        "order",
        "id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        ProgramExerciseInline,
    ]


@admin.register(ProgramExercise)
class ProgramExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program_day",
        "exercise",
        "sets",
        "reps",
        "rest_seconds",
        "weight",
        "order",
    )

    autocomplete_fields = (
        "exercise",
    )

    search_fields = (
        "exercise__name",
        "program_day__title",
        "program_day__program__student__user__phone",
    )

    ordering = (
        "program_day",
        "order",
        "id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )



@admin.register(NutritionDay)
class NutritionDayAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "program",
        "title",
        "order",
        "is_deleted",
    )

    list_filter = (
        "is_deleted",
    )

    search_fields = (
        "title",
        "program__student__user__phone",
    )

    ordering = (
        "program",
        "order",
        "id",
    )



# ---------------------------------------
# Nutrition Meal Admin
# ---------------------------------------

@admin.register(NutritionMeal)
class NutritionMealAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nutrition_day",
        "title",
        "meal_time",
        "order",
        "is_deleted",
    )

    list_filter = (
        "is_deleted",
    )

    search_fields = (
        "title",
        "nutrition_day__title",
        "nutrition_day__program__student__user__phone",
    )

    ordering = (
        "nutrition_day",
        "order",
        "id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def has_delete_permission(self, request, obj=None):
        return False



# ---------------------------------------
# Nutrition Food Item Admin
# ---------------------------------------

@admin.register(NutritionFoodItem)
class NutritionFoodItemAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "nutrition_meal",
        "quantity",
        "unit",
        "order",
        "is_deleted",
    )

    list_filter = (
        "unit",
        "is_deleted",
    )

    search_fields = (
        "name",
        "nutrition_meal__title",
        "nutrition_meal__nutrition_day__title",
    )

    ordering = (
        "nutrition_meal",
        "order",
        "id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def has_delete_permission(self, request, obj=None):
        return False