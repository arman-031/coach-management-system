from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Sum

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError
from orders.serializers import PurchaseOrderReadSerializer
from accounts.permissions import IsCoach
from programs.models import Program
from programs.services import expire_due_programs
from orders.models import PurchaseOrder

from .access import coach_student_users
from .serializers import StudentDetailSerializer


class CoachStudentOverviewView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get(self, request, pk):

        coach = request.user

        # Only students associated with this coach.
        student_user = get_object_or_404(
            coach_student_users(coach).select_related(
                "student_profile",
            ),
            pk=pk,
        )

        student = student_user.student_profile

        expire_due_programs()

        # Programs belonging to this coach.
        programs = Program.objects.filter(
            student=student,
            created_by=coach,
            is_deleted=False,
        )

        program_counts = programs.aggregate(
            total=Count("id"),
            waiting=Count(
                "id",
                filter=Q(status=Program.Status.WAITING),
            ),
            preparing=Count(
                "id",
                filter=Q(status=Program.Status.PREPARING),
            ),
            active=Count(
                "id",
                filter=Q(status=Program.Status.ACTIVE),
            ),
            expired=Count(
                "id",
                filter=Q(status=Program.Status.EXPIRED),
            ),
        )

        recent_programs = []

        for program in programs.select_related("questionnaire").order_by(
            "-created_at", "-id"
        )[:10]:
            questionnaire = getattr(
                program,
                "questionnaire",
                None,
            )

            recent_programs.append(
                {
                    "id": program.id,
                    "program_type": program.program_type,
                    "program_type_display": (program.get_program_type_display()),
                    "status": program.status,
                    "status_display": (program.get_status_display()),
                    "questionnaire_status": (
                        questionnaire.status if questionnaire is not None else None
                    ),
                    "published_at": program.published_at,
                    "expires_at": program.expires_at,
                }
            )

        # Orders belonging to this coach.
        orders = PurchaseOrder.objects.filter(
            student=student,
            coach=coach,
        )

        order_stats = orders.aggregate(
            total=Count("id"),
            paid=Count(
                "id",
                filter=Q(
                    status=PurchaseOrder.Status.PAID,
                ),
            ),
            revenue=Sum(
                "amount_irr",
                filter=Q(
                    status=PurchaseOrder.Status.PAID,
                ),
            ),
        )

        recent_orders = [
            {
                "id": order.id,
                "program_type": order.program_type,
                "status": order.status,
                "amount_irr": order.amount_irr,
                "program_id": order.program_id,
                "paid_at": order.paid_at,
            }
            for order in orders.order_by(
                "-created_at",
                "-id",
            )[:10]
        ]

        return Response(
            {
                "student": StudentDetailSerializer(student_user).data,
                "program_counts": program_counts,
                "recent_programs": recent_programs,
                "orders": {
                    "total": order_stats["total"],
                    "paid": order_stats["paid"],
                    "total_revenue_irr": (order_stats["revenue"] or 0),
                    "recent": recent_orders,
                    "student_profile_id": student.id,
                },
            }
        )


class CoachStudentOrdersView(ListAPIView):

    serializer_class = PurchaseOrderReadSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_queryset(self):

        coach = self.request.user

        student_user = get_object_or_404(
            coach_student_users(coach),
            pk=self.kwargs["pk"],
        )

        queryset = PurchaseOrder.objects.filter(
            coach=coach,
            student__user=student_user,
        ).select_related("program")

        # Optional filters.
        allowed_filters = {
            "status": PurchaseOrder.Status.values,
            "program_type": Program.ProgramType.values,
        }

        for field, allowed_values in allowed_filters.items():

            value = self.request.query_params.get(field)

            if value is None:
                continue

            if value not in allowed_values:
                raise ValidationError({field: "مقدار فیلتر معتبر نیست."})

            queryset = queryset.filter(**{field: value})

        return queryset.order_by(
            "-created_at",
            "-id",
        )
