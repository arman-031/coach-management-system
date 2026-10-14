from django.urls import path

from .views import (
    StudentOrderCreateView,
    StudentOrderListView,
)


urlpatterns = [
    path(
        "create/",
        StudentOrderCreateView.as_view(),
        name="student-order-create",
    ),

    path(
        "my/",
        StudentOrderListView.as_view(),
        name="student-order-list",
    ),
]