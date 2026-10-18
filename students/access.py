from django.db.models import Exists, OuterRef, Q

from accounts.models import User
from programs.models import Program
from orders.models import PurchaseOrder


def coach_student_users(coach):

    coach_programs = Program.objects.filter(
        student__user_id=OuterRef("pk"),
        created_by=coach,
        is_deleted=False,
    )

    coach_orders = PurchaseOrder.objects.filter(
        student__user_id=OuterRef("pk"),
        coach=coach,
    )

    return (
        User.objects.filter(
            role=User.Role.STUDENT,
        )
        .annotate(
            has_coach_program=Exists(coach_programs),
            has_coach_order=Exists(coach_orders),
        )
        .filter(Q(has_coach_program=True) | Q(has_coach_order=True))
    )
