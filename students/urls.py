from django.urls import path

from .views import StudentProfileView,StudentListView,StudentDetailView, StudentDeactivateView,StudentActivateView,StudentUpdateView


app_name = "students"


urlpatterns = [
    path("", StudentListView.as_view(), name="student-list"),
    path("profile/", StudentProfileView.as_view(), name="profile"),
    path("<int:pk>/", StudentDetailView.as_view(), name="student-detail"),
    path("<int:pk>/deactivate/",StudentDeactivateView.as_view(),name="student-deactivate",),
    path("<int:pk>/activate/",StudentActivateView.as_view(),name="student-activate",),
    path("<int:pk>/edit/",StudentUpdateView.as_view(),name="student-update",),
]