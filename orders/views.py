from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError

from .gateways.registry import get_active_gateway
from .payment_services import start_order_payment
from accounts.models import User
from accounts.permissions import IsStudent
from students.models import StudentProfile

from .models import PurchaseOrder, PaymentAttempt
from .pricing import PROGRAM_PRICES_IRR
from .serializers import (
    PurchaseOrderCreateSerializer,
    PurchaseOrderReadSerializer,
    PaymentAttemptReadSerializer,
)


class StudentOrderCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def post(self, request):

        serializer = PurchaseOrderCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        program_type = serializer.validated_data["program_type"]

        # Get the price from the backend.
        amount = PROGRAM_PRICES_IRR.get(program_type)

        if amount is None:
            return Response(
                {"detail": "قیمت این نوع برنامه تعریف نشده است."},
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
            ).order_by(
                "id"
            )[:2]
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
        return (
            PurchaseOrder.objects.filter(
                student__user=self.request.user,
            )
            .select_related(
                "program",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )


class StudentOrderPaymentsView(ListAPIView):

    serializer_class = PaymentAttemptReadSerializer

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def get_queryset(self):

        order = get_object_or_404(
            PurchaseOrder,
            pk=self.kwargs["order_id"],
            student__user=self.request.user,
        )

        return PaymentAttempt.objects.filter(
            order=order,
        ).order_by(
            "-created_at",
            "-id",
        )



class StudentStartPaymentView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def post(self, request, order_id):

        # Step 1: Check order ownership.
        order = get_object_or_404(
            PurchaseOrder,
            pk=order_id,
            student__user=request.user,
        )

        # Step 2: Reject unexpected request data.
        if request.data:
            return Response(
                {
                    "detail": "این درخواست نباید بدنه داشته باشد."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 3: Only pending orders can be paid.
        if order.status != PurchaseOrder.Status.PENDING:
            return Response(
                {
                    "detail": "این سفارش قابل پرداخت نیست."
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Step 4: Select a trusted gateway.
        active_gateway = get_active_gateway()

        if active_gateway is None:
            return Response(
                {
                    "detail": "درگاه پرداخت هنوز فعال نشده است."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        provider, gateway = active_gateway

        # Step 5: Read callback URL from settings.
        callback_url = getattr(
            settings,
            "PAYMENT_CALLBACK_URL",
            "",
        )

        if not callback_url:
            return Response(
                {
                    "detail": "آدرس بازگشت پرداخت تنظیم نشده است."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Step 6: Start payment.
        try:
            attempt, result = start_order_payment(
                order_id=order.id,
                gateway=gateway,
                provider=provider,
                callback_url=callback_url,
            )

        # Handle order validation errors.
        except DjangoValidationError as exc:
            return Response(
                {
                    "detail": exc.messages
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Handle gateway connection problems.
        except (TimeoutError, ConnectionError):
            return Response(
                {
                    "detail": (
                        "ارتباط با درگاه پرداخت برقرار نشد. "
                        "وضعیت پرداخت در حال بررسی است. "
                        "لطفاً پرداخت جدیدی آغاز نکنید."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Step 7: Return payment information.
        return Response(
            {
                "attempt_id": attempt.id,
                "tracking_id": str(attempt.tracking_id),
                "status": attempt.status,
                "payment_url": result.payment_url,
            },
            status=status.HTTP_201_CREATED,
        )
