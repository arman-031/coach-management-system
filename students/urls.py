from django.urls import path

from .views import (
    StudentProfileView,
    StudentListView,
    StudentDetailView,
    StudentDeactivateView,
    StudentActivateView,
    StudentUpdateView,
)

from .coach_views import CoachStudentOverviewView, CoachStudentOrdersView

app_name = "students"


urlpatterns = [
    # Student's own profile
    path(
        "profile/",
        StudentProfileView.as_view(),
        name="profile",
    ),
    # Coach: Student list
    path(
        "",
        StudentListView.as_view(),
        name="student-list",
    ),
    # Coach: Student overview
    path(
        "<int:pk>/overview/",
        CoachStudentOverviewView.as_view(),
        name="coach-student-overview",
    ),
    # Coach: Student activation
    path(
        "<int:pk>/deactivate/",
        StudentDeactivateView.as_view(),
        name="student-deactivate",
    ),
    path(
        "<int:pk>/activate/",
        StudentActivateView.as_view(),
        name="student-activate",
    ),
    # Coach: Student update
    path(
        "<int:pk>/edit/",
        StudentUpdateView.as_view(),
        name="student-update",
    ),
    # Coach: Student detail
    path(
        "<int:pk>/",
        StudentDetailView.as_view(),
        name="student-detail",
    ),
    path(
        "<int:pk>/orders/",
        CoachStudentOrdersView.as_view(),
        name="coach-student-orders",
    ),
]
