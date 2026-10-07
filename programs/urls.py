from django.urls import path

from .views import (
    ProgramDetailView,
    ProgramListView,
    ProgramCreateView,
    ProgramStartPreparingView,
    ProgramPublishView
)


urlpatterns = [
    path(
        "",
        ProgramListView.as_view(),
        name="program-list",
    ),

    path(
        "<int:pk>/",
        ProgramDetailView.as_view(),
        name="program-detail",
    ),
    path(
    "create/",
    ProgramCreateView.as_view(),
    name="program-create",
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
]