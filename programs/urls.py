from django.urls import path

# ---------------------------------------
# Nutrition Views
# ---------------------------------------

from .nutrition_views import (
    NutritionDayListCreateView,
    NutritionDayDetailView,
    NutritionDayRestoreView,
    NutritionMealListCreateView,
    NutritionMealDetailView,
    NutritionMealRestoreView,
    NutritionFoodItemListCreateView,
    NutritionFoodItemDetailView,
    NutritionFoodItemRestoreView,
)

# ---------------------------------------
# Coach Program Views
# ---------------------------------------

from .views import (
    ProgramListView,
    ProgramDetailView,
    ProgramRestoreView,
    ProgramCreateView,
    ProgramStartPreparingView,
    ProgramPublishView,
    ProgramDayListCreateView,
    ProgramDayDetailView,
    ProgramDayRestoreView,
    ProgramExerciseCreateView,
    ProgramExerciseDetailView,
    ProgramExerciseRestoreView,
)

# ---------------------------------------
# Student Program Views
# ---------------------------------------

from .student_views import (
    StudentProgramListView,
    StudentProgramDetailView,
)


urlpatterns = [

    # ===================================
    # Student APIs
    # ===================================

    path(
        "my/",
        StudentProgramListView.as_view(),
        name="student-program-list",
    ),

    path(
        "my/<int:pk>/",
        StudentProgramDetailView.as_view(),
        name="student-program-detail",
    ),


    # ===================================
    # Coach Program APIs
    # ===================================

    path(
        "",
        ProgramListView.as_view(),
        name="program-list",
    ),

    path(
        "create/",
        ProgramCreateView.as_view(),
        name="program-create",
    ),

    path(
        "<int:pk>/restore/",
        ProgramRestoreView.as_view(),
        name="program-restore",
    ),

    path(
        "<int:pk>/start-preparing/",
        ProgramStartPreparingView.as_view(),
        name="program-start-preparing",
    ),

    path(
        "<int:pk>/publish/",
        ProgramPublishView.as_view(),
        name="program-publish",
    ),


    # ===================================
    # ProgramDay APIs
    # ===================================

    path(
        "<int:program_pk>/days/",
        ProgramDayListCreateView.as_view(),
        name="program-day-list-create",
    ),

    path(
        "<int:program_pk>/days/<int:pk>/restore/",
        ProgramDayRestoreView.as_view(),
        name="program-day-restore",
    ),

    path(
        "<int:program_pk>/days/<int:pk>/",
        ProgramDayDetailView.as_view(),
        name="program-day-detail",
    ),


    # ===================================
    # ProgramExercise APIs
    # ===================================

    path(
        "<int:program_pk>/days/<int:day_pk>/exercises/",
        ProgramExerciseCreateView.as_view(),
        name="program-exercise-create",
    ),

    path(
        "<int:program_pk>/days/<int:day_pk>/exercises/<int:pk>/restore/",
        ProgramExerciseRestoreView.as_view(),
        name="program-exercise-restore",
    ),

    path(
        "<int:program_pk>/days/<int:day_pk>/exercises/<int:pk>/",
        ProgramExerciseDetailView.as_view(),
        name="program-exercise-detail",
    ),


    # ===================================
    # NutritionDay APIs
    # ===================================

    path(
        "<int:program_pk>/nutrition-days/",
        NutritionDayListCreateView.as_view(),
        name="nutrition-day-list-create",
    ),

    path(
        "<int:program_pk>/nutrition-days/<int:pk>/restore/",
        NutritionDayRestoreView.as_view(),
        name="nutrition-day-restore",
    ),

    path(
        "<int:program_pk>/nutrition-days/<int:pk>/",
        NutritionDayDetailView.as_view(),
        name="nutrition-day-detail",
    ),


    # ===================================
    # Program Detail
    # Keep generic route at the end
    # ===================================

    path(
        "<int:pk>/",
        ProgramDetailView.as_view(),
        name="program-detail",
    ),
    path(
        "<int:program_pk>/nutrition-days/<int:day_pk>/meals/",
        NutritionMealListCreateView.as_view(),
        name="nutrition-meal-list-create",
    ),
    path(
        "<int:program_pk>/nutrition-days/<int:day_pk>/meals/<int:pk>/restore/",
        NutritionMealRestoreView.as_view(),
        name="nutrition-meal-restore",
    ),

    path(
        "<int:program_pk>/nutrition-days/<int:day_pk>/meals/<int:pk>/",
        NutritionMealDetailView.as_view(),
        name="nutrition-meal-detail",
    ),
    path(
        "<int:program_pk>/nutrition-days/<int:day_pk>/meals/<int:meal_pk>/food-items/",
        NutritionFoodItemListCreateView.as_view(),
        name="nutrition-food-item-list-create",
    ),
    path(
        "<int:program_pk>/nutrition-days/<int:day_pk>/meals/<int:meal_pk>/food-items/<int:pk>/restore/",
        NutritionFoodItemRestoreView.as_view(),
        name="nutrition-food-item-restore",
    ),

    path(
        "<int:program_pk>/nutrition-days/<int:day_pk>/meals/<int:meal_pk>/food-items/<int:pk>/",
        NutritionFoodItemDetailView.as_view(),
        name="nutrition-food-item-detail",
    ),

]