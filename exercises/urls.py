from django.urls import path

from .views import ExerciseListView,ExerciseCreateView,MuscleGroupListView,ExerciseUpdateView,ExerciseDeactivateView,ExerciseActivateView


app_name = "exercises"


urlpatterns = [
    path("", ExerciseListView.as_view(), name="exercise-list"),
    path("create/",ExerciseCreateView.as_view(),name="exercise-create",),
    path("muscle-groups/",MuscleGroupListView.as_view(),name="muscle-group-list",),
    path("<int:pk>/edit/",ExerciseUpdateView.as_view(),name="exercise-update"),
    path("<int:pk>/deactivate/",ExerciseDeactivateView.as_view(),name="exercise-deactivate"),
    path("<int:pk>/activate/",ExerciseActivateView.as_view(),name="exercise-activate"),
]