from django.db.models import (
    Count,
    Q,
    Sum,
)
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsCoach
from students.models import StudentProfile
from questionnaires.models import ProgramQuestionnaire
from orders.models import PurchaseOrder

from .models import Program


class CoachDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get(self, request):

        coach = request.user
        now = timezone.now()

        # ----------------------------------
        # 1. Coach's associated students
        # ----------------------------------

        students_count = (
            StudentProfile.objects.filter(
                Q(
                    programs__created_by=coach,
                    programs__is_deleted=False,
                )
                | Q(
                    purchase_orders__coach=coach,
                )
            )
            .distinct()
            .count()
        )

        # ----------------------------------
        # 2. Coach's programs
        # ----------------------------------

        programs = Program.objects.filter(
            created_by=coach,
            is_deleted=False,
        )

        program_stats = programs.aggregate(
            total=Count("id"),
            waiting=Count(
                "id",
                filter=Q(
                    status=Program.Status.WAITING,
                ),
            ),
            preparing=Count(
                "id",
                filter=Q(
                    status=Program.Status.PREPARING,
                ),
            ),
            active=Count(
                "id",
                filter=Q(
                    status=Program.Status.ACTIVE,
                )
                & (Q(expires_at__gt=now) | Q(expires_at__isnull=True)),
            ),
            expired=Count(
                "id",
                filter=(
                    Q(status=Program.Status.EXPIRED)
                    | Q(
                        status=Program.Status.ACTIVE,
                        expires_at__lte=now,
                    )
                ),
            ),
        )

        # ----------------------------------
        # 3. Verified paid orders
        # ----------------------------------

        paid_orders = PurchaseOrder.objects.filter(
            coach=coach,
            status=PurchaseOrder.Status.PAID,
        )

        payment_stats = paid_orders.aggregate(
            paid_orders_count=Count("id"),
            revenue=Sum("amount_irr"),
        )

        revenue_irr = payment_stats["revenue"] or 0

        # ----------------------------------
        # 4. Submitted questionnaires
        # ----------------------------------

        submitted_questionnaires_count = ProgramQuestionnaire.objects.filter(
            program__created_by=coach,
            program__is_deleted=False,
            program__status=Program.Status.PREPARING,
            status=ProgramQuestionnaire.Status.SUBMITTED,
        ).count()

        # ----------------------------------
        # 5. Recent preparing programs
        # ----------------------------------

        preparing_programs = (
            programs.filter(
                status=Program.Status.PREPARING,
            )
            .select_related(
                "student__user",
            )
            .order_by("-created_at", "-id")[:5]
        )

        recent_preparing = [
            {
                "id": program.id,
                "student_phone": program.student.user.phone,
                "program_type": program.program_type,
                "status": program.status,
            }
            for program in preparing_programs
        ]

        # ----------------------------------
        # 6. Recent paid orders
        # ----------------------------------

        recent_orders = paid_orders.select_related(
            "student__user",
        ).order_by(
            "-paid_at", "-id"
        )[:5]

        recent_paid = [
            {
                "id": order.id,
                "student_phone": order.student.user.phone,
                "program_type": order.program_type,
                "amount_irr": order.amount_irr,
                "paid_at": order.paid_at,
            }
            for order in recent_orders
        ]

        # ----------------------------------
        # 7. Dashboard response
        # ----------------------------------

        return Response(
            {
                "students_count": students_count,
                "programs": program_stats,
                "payments": {
                    "paid_orders_count": payment_stats["paid_orders_count"],
                    "total_revenue_irr": revenue_irr,
                },
                "actions": {
                    "preparing_programs_count": (program_stats["preparing"]),
                    "submitted_questionnaires_count": (submitted_questionnaires_count),
                },
                "recent_preparing_programs": recent_preparing,
                "recent_paid_orders": recent_paid,
            }
        )
