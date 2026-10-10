from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCoach

from .models import (
    Program,
    NutritionDay,
    NutritionMeal,
    NutritionFoodItem,
)

from .nutrition_serializers import (
    NutritionDaySerializer,
    NutritionMealSerializer,
    NutritionFoodItemSerializer,
)


# ---------------------------------------
# Nutrition Day List + Create
# GET / POST
# ---------------------------------------

class NutritionDayListCreateView(ListCreateAPIView):

    serializer_class = NutritionDaySerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_program(self):
        program = get_object_or_404(
            Program,
            pk=self.kwargs["program_pk"],
            created_by=self.request.user,
            is_deleted=False,
        )

        if program.program_type != Program.ProgramType.NUTRITION:
            raise ValidationError({
                "detail": (
                    "این عملیات فقط برای "
                    "برنامه‌های تغذیه مجاز است."
                )
            })

        return program

    def get_queryset(self):
        program = self.get_program()

        return NutritionDay.objects.filter(
            program=program,
            is_deleted=False,
        ).order_by(
            "order",
            "id",
        )

    def perform_create(self, serializer):
        program = self.get_program()

        serializer.save(
            program=program,
        )


# ---------------------------------------
# Nutrition Day Detail + Update + Delete
# GET / PATCH / DELETE
# ---------------------------------------

class NutritionDayDetailView(RetrieveUpdateDestroyAPIView):

    serializer_class = NutritionDaySerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    http_method_names = [
        "get",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return NutritionDay.objects.filter(
            program_id=self.kwargs["program_pk"],
            program__created_by=self.request.user,
            program__program_type=Program.ProgramType.NUTRITION,
            program__is_deleted=False,
            is_deleted=False,
        ).select_related(
            "program",
        )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()

        instance.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )


# ---------------------------------------
# Nutrition Day Restore
# PATCH
# ---------------------------------------

class NutritionDayRestoreView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, program_pk, pk):
        nutrition_day = get_object_or_404(
            NutritionDay.objects.select_related("program"),
            pk=pk,
            program_id=program_pk,
            program__created_by=request.user,
            program__program_type=Program.ProgramType.NUTRITION,
            program__is_deleted=False,
        )

        if not nutrition_day.is_deleted:
            return Response(
                {
                    "detail": (
                        "این روز تغذیه فعال است و "
                        "نیازی به بازیابی ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nutrition_day.is_deleted = False
        nutrition_day.deleted_at = None

        nutrition_day.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )

        serializer = NutritionDaySerializer(
            nutrition_day,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------
# Nutrition Meal List + Create
# GET / POST
# ---------------------------------------

class NutritionMealListCreateView(ListCreateAPIView):

    serializer_class = NutritionMealSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_day(self):
        return get_object_or_404(
            NutritionDay.objects.select_related("program"),
            pk=self.kwargs["day_pk"],
            program_id=self.kwargs["program_pk"],
            program__created_by=self.request.user,
            program__program_type=Program.ProgramType.NUTRITION,
            program__is_deleted=False,
            is_deleted=False,
        )

    def get_queryset(self):
        nutrition_day = self.get_day()

        return NutritionMeal.objects.filter(
            nutrition_day=nutrition_day,
            is_deleted=False,
        ).order_by(
            "order",
            "id",
        )

    def perform_create(self, serializer):
        nutrition_day = self.get_day()

        serializer.save(
            nutrition_day=nutrition_day,
        )


# ---------------------------------------
# Nutrition Meal Detail + Update + Delete
# GET / PATCH / DELETE
# ---------------------------------------

class NutritionMealDetailView(RetrieveUpdateDestroyAPIView):

    serializer_class = NutritionMealSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    http_method_names = [
        "get",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return NutritionMeal.objects.filter(
            nutrition_day_id=self.kwargs["day_pk"],
            nutrition_day__program_id=self.kwargs["program_pk"],
            nutrition_day__program__created_by=self.request.user,
            nutrition_day__program__program_type=Program.ProgramType.NUTRITION,
            nutrition_day__program__is_deleted=False,
            nutrition_day__is_deleted=False,
            is_deleted=False,
        ).select_related(
            "nutrition_day",
            "nutrition_day__program",
        )

    def perform_destroy(self, instance):
        # Soft delete: keep the meal in PostgreSQL.
        instance.is_deleted = True
        instance.deleted_at = timezone.now()

        instance.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )


# ---------------------------------------
# Nutrition Meal Restore
# PATCH
# ---------------------------------------

class NutritionMealRestoreView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, program_pk, day_pk, pk):
        nutrition_meal = get_object_or_404(
            NutritionMeal.objects.select_related(
                "nutrition_day",
                "nutrition_day__program",
            ),
            pk=pk,
            nutrition_day_id=day_pk,
            nutrition_day__program_id=program_pk,
            nutrition_day__program__created_by=request.user,
            nutrition_day__program__program_type=Program.ProgramType.NUTRITION,
            nutrition_day__program__is_deleted=False,
            nutrition_day__is_deleted=False,
        )

        if not nutrition_meal.is_deleted:
            return Response(
                {
                    "detail": (
                        "این وعده غذایی فعال است و "
                        "نیازی به بازیابی ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nutrition_meal.is_deleted = False
        nutrition_meal.deleted_at = None

        nutrition_meal.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )

        serializer = NutritionMealSerializer(
            nutrition_meal,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )



# ---------------------------------------
# Nutrition Food Item List + Create
# GET / POST
# ---------------------------------------

class NutritionFoodItemListCreateView(ListCreateAPIView):

    serializer_class = NutritionFoodItemSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_meal(self):
        return get_object_or_404(
            NutritionMeal.objects.select_related(
                "nutrition_day",
                "nutrition_day__program",
            ),

            pk=self.kwargs["meal_pk"],

            nutrition_day_id=self.kwargs["day_pk"],

            nutrition_day__program_id=self.kwargs["program_pk"],

            nutrition_day__program__created_by=self.request.user,

            nutrition_day__program__program_type=(
                Program.ProgramType.NUTRITION
            ),

            nutrition_day__program__is_deleted=False,

            nutrition_day__is_deleted=False,

            is_deleted=False,
        )

    def get_queryset(self):
        nutrition_meal = self.get_meal()

        return NutritionFoodItem.objects.filter(
            nutrition_meal=nutrition_meal,
            is_deleted=False,
        ).order_by(
            "order",
            "id",
        )

    def perform_create(self, serializer):
        nutrition_meal = self.get_meal()

        serializer.save(
            nutrition_meal=nutrition_meal,
        )


# ---------------------------------------
# Nutrition Food Item Detail
# GET / PATCH / DELETE
# ---------------------------------------

class NutritionFoodItemDetailView(
    RetrieveUpdateDestroyAPIView
):
    serializer_class = NutritionFoodItemSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    http_method_names = [
        "get",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return NutritionFoodItem.objects.filter(
            nutrition_meal_id=self.kwargs["meal_pk"],

            nutrition_meal__nutrition_day_id=(
                self.kwargs["day_pk"]
            ),

            nutrition_meal__nutrition_day__program_id=(
                self.kwargs["program_pk"]
            ),

            nutrition_meal__nutrition_day__program__created_by=(
                self.request.user
            ),

            nutrition_meal__nutrition_day__program__program_type=(
                Program.ProgramType.NUTRITION
            ),

            nutrition_meal__nutrition_day__program__is_deleted=False,

            nutrition_meal__nutrition_day__is_deleted=False,

            nutrition_meal__is_deleted=False,

            is_deleted=False,

        ).select_related(
            "nutrition_meal",
            "nutrition_meal__nutrition_day",
            "nutrition_meal__nutrition_day__program",
        )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()

        instance.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )


# ---------------------------------------
# Nutrition Food Item Restore
# PATCH
# ---------------------------------------

class NutritionFoodItemRestoreView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, program_pk, day_pk, meal_pk, pk):

        food_item = get_object_or_404(
            NutritionFoodItem.objects.select_related(
                "nutrition_meal",
                "nutrition_meal__nutrition_day",
                "nutrition_meal__nutrition_day__program",
            ),

            pk=pk,

            nutrition_meal_id=meal_pk,

            nutrition_meal__nutrition_day_id=day_pk,

            nutrition_meal__nutrition_day__program_id=program_pk,

            nutrition_meal__nutrition_day__program__created_by=(
                request.user
            ),

            nutrition_meal__nutrition_day__program__program_type=(
                Program.ProgramType.NUTRITION
            ),

            nutrition_meal__nutrition_day__program__is_deleted=False,

            nutrition_meal__nutrition_day__is_deleted=False,

            nutrition_meal__is_deleted=False,
        )

        if not food_item.is_deleted:
            return Response(
                {
                    "detail": (
                        "این ماده غذایی فعال است و "
                        "نیازی به بازیابی ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        food_item.is_deleted = False
        food_item.deleted_at = None

        food_item.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )

        serializer = NutritionFoodItemSerializer(
            food_item,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )