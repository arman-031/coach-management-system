from django.urls import path

from .views import (
    ExerciseActivateView,
    ExerciseCopyView,
    ExerciseCreateView,
    ExerciseDeactivateView,
    ExerciseListView,
    ExerciseDetailView,
    ExerciseMediaCreateView,
    ExerciseMediaDeleteView,
    ExerciseMediaUpdateView,
    ExerciseUpdateView,
    MuscleGroupListView,
)

app_name = "exercises"


urlpatterns = [
    path("", ExerciseListView.as_view(), name="exercise-list"),
    path("create/", ExerciseCreateView.as_view(), name="exercise-create"),
    path(
        "muscle-groups/",
        MuscleGroupListView.as_view(),
        name="muscle-group-list",
    ),
    path("<int:pk>/edit/", ExerciseUpdateView.as_view(), name="exercise-update"),
    path(
        "<int:pk>/deactivate/",
        ExerciseDeactivateView.as_view(),
        name="exercise-deactivate",
    ),
    path(
        "<int:pk>/activate/",
        ExerciseActivateView.as_view(),
        name="exercise-activate",
    ),
    path("<int:pk>/copy/", ExerciseCopyView.as_view(), name="exercise-copy"),
    path(
        "<int:pk>/media/",
        ExerciseMediaCreateView.as_view(),
        name="exercise-media-create",
    ),
    path(
        "<int:exercise_pk>/media/<int:pk>/edit/",
        ExerciseMediaUpdateView.as_view(),
        name="exercise-media-update",
    ),
    path(
        "<int:exercise_pk>/media/<int:pk>/delete/",
        ExerciseMediaDeleteView.as_view(),
        name="exercise-media-delete",
    ),
    path("<int:pk>/", ExerciseDetailView.as_view(), name="exercise-detail"),
]
