

from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsStudent
from students.models import StudentProfile

from .models import PurchaseOrder
from .pricing import PROGRAM_PRICES_IRR
from .serializers import (
    PurchaseOrderCreateSerializer,
    PurchaseOrderReadSerializer,
)


class StudentOrderCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def post(self, request):

        serializer = PurchaseOrderCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        program_type = serializer.validated_data[
            "program_type"
        ]

        # Get the price from the backend.
        amount = PROGRAM_PRICES_IRR.get(program_type)

        if amount is None:
            return Response(
                {
                    "detail": "قیمت این نوع برنامه تعریف نشده است."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the authenticated student's profile.
        student = get_object_or_404(
            StudentProfile,
            user=request.user,
        )

        # Current project supports one main coach.
        coaches = list(
            User.objects.filter(
                role=User.Role.COACH,
                is_active=True,
            ).order_by("id")[:2]
        )

        if len(coaches) != 1:
            return Response(
                {
                    "detail": (
                        "مربی اصلی سیستم مشخص نیست. "
                        "باید دقیقاً یک حساب مربی فعال وجود داشته باشد."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Create an unpaid order.
        order = PurchaseOrder.objects.create(
            student=student,
            coach=coaches[0],
            program_type=program_type,
            amount_irr=amount,
        )

        output = PurchaseOrderReadSerializer(order)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )


class StudentOrderListView(ListAPIView):

    serializer_class = PurchaseOrderReadSerializer

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            student__user=self.request.user,
        ).select_related(
            "program",
        ).order_by(
            "-created_at",
            "-id",
        )