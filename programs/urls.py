from django.urls import path

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

from .student_views import (
    StudentProgramListView,
    StudentProgramDetailView,
)


urlpatterns = [
    # Student APIs
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

    # Coach Program APIs
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

    path(
        "<int:pk>/",
        ProgramDetailView.as_view(),
        name="program-detail",
    ),
]