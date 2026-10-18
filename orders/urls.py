from django.urls import path

from .views import (
    StudentOrderCreateView,
    StudentOrderListView,
    StudentOrderPaymentsView,
    StudentStartPaymentView,
    ZarinpalCallbackView,
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
    path(
        "my/<int:order_id>/payments/",
        StudentOrderPaymentsView.as_view(),
        name="student-order-payments",
    ),
    path(
        "my/<int:order_id>/payments/start/",
        StudentStartPaymentView.as_view(),
        name="student-start-payment",
    ),
    path(
        "payments/zarinpal/callback/",
        ZarinpalCallbackView.as_view(),
        name="zarinpal-callback",
    ),
]
