from django.db.models import Prefetch

from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)

from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
)

from .models import (
    Program,
    ProgramDay,
    ProgramExercise,
    NutritionDay,
    NutritionMeal,
    NutritionFoodItem,
)

from .student_serializers import (
    StudentProgramListSerializer,
    StudentProgramDetailSerializer,
)

from .services import expire_due_programs


# ---------------------------------------
# Student Permission
# ---------------------------------------

class IsStudent(BasePermission):

    message = "فقط شاگردان به این بخش دسترسی دارند."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "STUDENT"
        )


# ---------------------------------------
# Student Program List
# GET
# ---------------------------------------

class StudentProgramListView(ListAPIView):

    serializer_class = StudentProgramListSerializer

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def get_queryset(self):

        expire_due_programs()

        return Program.objects.filter(
            student__user=self.request.user,
            is_deleted=False,
            status__in=[
                Program.Status.ACTIVE,
                Program.Status.EXPIRED,
            ],
        ).order_by(
            "-published_at",
        )


# ---------------------------------------
# Student Program Detail
# GET
# ---------------------------------------

class StudentProgramDetailView(RetrieveAPIView):

    serializer_class = StudentProgramDetailSerializer

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def get_queryset(self):

        expire_due_programs()

        # -----------------------------------
        # Active workout exercises
        # -----------------------------------

        active_exercises = (
            ProgramExercise.objects.filter(
                is_deleted=False,
            ).select_related(
                "exercise",
            ).prefetch_related(
                "exercise__media",
            )
        )

        # -----------------------------------
        # Active workout days
        # -----------------------------------

        active_workout_days = (
            ProgramDay.objects.filter(
                is_deleted=False,
            ).order_by(
                "order",
                "id",
            ).prefetch_related(
                Prefetch(
                    "exercises",
                    queryset=active_exercises,
                )
            )
        )

        # -----------------------------------
        # Active nutrition food items
        # -----------------------------------

        active_food_items = (
            NutritionFoodItem.objects.filter(
                is_deleted=False,
            ).order_by(
                "order",
                "id",
            )
        )

        # -----------------------------------
        # Active nutrition meals
        # -----------------------------------

        active_meals = (
            NutritionMeal.objects.filter(
                is_deleted=False,
            ).order_by(
                "order",
                "id",
            ).prefetch_related(
                Prefetch(
                    "food_items",
                    queryset=active_food_items,
                )
            )
        )

        # -----------------------------------
        # Active nutrition days
        # -----------------------------------

        active_nutrition_days = (
            NutritionDay.objects.filter(
                is_deleted=False,
            ).order_by(
                "order",
                "id",
            ).prefetch_related(
                Prefetch(
                    "meals",
                    queryset=active_meals,
                )
            )
        )

        # -----------------------------------
        # Return student's own program
        # -----------------------------------

        return Program.objects.filter(
            student__user=self.request.user,
            is_deleted=False,
            status__in=[
                Program.Status.ACTIVE,
                Program.Status.EXPIRED,
            ],
        ).prefetch_related(

            Prefetch(
                "days",
                queryset=active_workout_days,
            ),

            Prefetch(
                "nutrition_days",
                queryset=active_nutrition_days,
            ),

        )