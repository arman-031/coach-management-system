from datetime import timedelta

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveDestroyAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCoach

from .models import (
    Program,
    ProgramDay,
    ProgramExercise,
    NutritionFoodItem,
)
from .serializers import (
    ProgramCreateSerializer,
    ProgramDetailSerializer,
    ProgramListSerializer,
    ProgramDayCreateSerializer,
    ProgramDayListSerializer,
    ProgramExerciseCreateSerializer,
    ProgramExerciseReadSerializer,
)
from .services import expire_due_programs


# ---------------------------------------
# Helper: Active program exercises
# ---------------------------------------

def active_program_exercises():
    return Prefetch(
        "exercises",
        queryset=ProgramExercise.objects.filter(
            is_deleted=False,
        ).select_related(
            "exercise",
        ).prefetch_related(
            "exercise__media",
        ),
    )


# ---------------------------------------
# Program List
# GET
# ---------------------------------------

class ProgramListView(ListAPIView):
    serializer_class = ProgramListSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    filterset_fields = (
        "program_type",
        "status",
        "student",
    )

    search_fields = (
        "student__user__phone",
    )

    ordering_fields = (
        "created_at",
        "published_at",
        "expires_at",
    )

    ordering = ("-created_at",)

    def get_queryset(self):
        expire_due_programs()

        return Program.objects.filter(
            created_by=self.request.user,
            is_deleted=False,
        ).select_related(
            "student",
            "student__user",
            "created_by",
        )


# ---------------------------------------
# Program Detail + Soft Delete
# GET / DELETE
# ---------------------------------------

class ProgramDetailView(RetrieveDestroyAPIView):
    serializer_class = ProgramDetailSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    http_method_names = [
        "get",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        expire_due_programs()

        return Program.objects.filter(
            created_by=self.request.user,
            is_deleted=False,
        ).select_related(
            "student",
            "student__user",
            "created_by",
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
# Program Restore
# PATCH
# ---------------------------------------

class ProgramRestoreView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        program = get_object_or_404(
            Program.objects.select_related(
                "student",
                "student__user",
                "created_by",
            ),
            pk=pk,
            created_by=request.user,
        )

        if not program.is_deleted:
            return Response(
                {
                    "detail": (
                        "این برنامه فعال است و "
                        "نیازی به بازیابی ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        program.is_deleted = False
        program.deleted_at = None

        update_fields = [
            "is_deleted",
            "deleted_at",
            "updated_at",
        ]

        # If the original expiration date has passed,
        # restore the program as EXPIRED, not ACTIVE.
        if (
            program.status == Program.Status.ACTIVE
            and program.expires_at is not None
            and program.expires_at <= timezone.now()
        ):
            program.status = Program.Status.EXPIRED
            update_fields.append("status")

        program.save(
            update_fields=update_fields,
        )

        serializer = ProgramDetailSerializer(
            program,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------
# Program Create
# POST
# ---------------------------------------

class ProgramCreateView(CreateAPIView):
    serializer_class = ProgramCreateSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
        )


# ---------------------------------------
# Start Preparing
# WAITING -> PREPARING
# PATCH
# ---------------------------------------

class ProgramStartPreparingView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        program = get_object_or_404(
            Program,
            pk=pk,
            created_by=request.user,
            is_deleted=False,
        )

        if program.status != Program.Status.WAITING:
            return Response(
                {
                    "detail": (
                        "فقط برنامه در انتظار را می‌توان "
                        "وارد مرحله آماده‌سازی کرد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        program.status = Program.Status.PREPARING

        program.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = ProgramDetailSerializer(
            program,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------
# Publish Program
# PREPARING -> ACTIVE
# PATCH
# ---------------------------------------

# ---------------------------------------
# Publish Program
# PREPARING -> ACTIVE
# PATCH
# ---------------------------------------

class ProgramPublishView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):

        # Find the coach's program.
        program = get_object_or_404(
            Program,
            pk=pk,
            created_by=request.user,
            is_deleted=False,
        )

        # Only preparing programs can be published.
        if program.status != Program.Status.PREPARING:
            return Response(
                {
                    "detail": (
                        "فقط برنامه در حال آماده‌سازی "
                        "را می‌توان منتشر کرد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------
        # Validate bodybuilding / corrective
        # -----------------------------------

        if program.program_type in (
            Program.ProgramType.BODYBUILDING,
            Program.ProgramType.CORRECTIVE,
        ):

            has_exercise = ProgramDay.objects.filter(
                program=program,
                is_deleted=False,
                exercises__is_deleted=False,
            ).exists()

            if not has_exercise:
                return Response(
                    {
                        "detail": (
                            "برای انتشار برنامه تمرینی "
                            "باید حداقل یک جلسه فعال "
                            "با یک حرکت فعال وجود داشته باشد."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -----------------------------------
        # Validate nutrition program
        # -----------------------------------

        if program.program_type == Program.ProgramType.NUTRITION:

            has_food_item = NutritionFoodItem.objects.filter(
                nutrition_meal__nutrition_day__program=program,
                nutrition_meal__nutrition_day__is_deleted=False,
                nutrition_meal__is_deleted=False,
                is_deleted=False,
            ).exists()

            if not has_food_item:
                return Response(
                    {
                        "detail": (
                            "برای انتشار برنامه تغذیه "
                            "باید حداقل یک روز فعال، "
                            "یک وعده فعال و یک ماده غذایی "
                            "فعال وجود داشته باشد."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -----------------------------------
        # Publish the program
        # -----------------------------------

        published_at = timezone.now()

        program.status = Program.Status.ACTIVE
        program.published_at = published_at

        program.expires_at = published_at + timedelta(
            days=program.duration_days,
        )

        program.save(
            update_fields=[
                "status",
                "published_at",
                "expires_at",
                "updated_at",
            ]
        )

        serializer = ProgramDetailSerializer(
            program,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        program = get_object_or_404(
            Program,
            pk=pk,
            created_by=request.user,
            is_deleted=False,
        )

        if program.status != Program.Status.PREPARING:
            return Response(
                {
                    "detail": (
                        "فقط برنامه در حال آماده‌سازی "
                        "را می‌توان منتشر کرد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate workout content before publication.
        if program.program_type in (
            Program.ProgramType.BODYBUILDING,
            Program.ProgramType.CORRECTIVE,
        ):
            has_exercise = ProgramDay.objects.filter(
                program=program,
                is_deleted=False,
                exercises__is_deleted=False,
            ).exists()

            if not has_exercise:
                return Response(
                    {
                        "detail": (
                            "برای انتشار برنامه باید "
                            "حداقل یک جلسه فعال با "
                            "یک حرکت فعال وجود داشته باشد."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        published_at = timezone.now()

        program.status = Program.Status.ACTIVE
        program.published_at = published_at

        program.expires_at = published_at + timedelta(
            days=program.duration_days,
        )

        program.save(
            update_fields=[
                "status",
                "published_at",
                "expires_at",
                "updated_at",
            ]
        )

        serializer = ProgramDetailSerializer(
            program,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------
# ProgramDay List + Create
# GET / POST
# ---------------------------------------

class ProgramDayListCreateView(ListCreateAPIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProgramDayCreateSerializer

        return ProgramDayListSerializer

    def get_program(self):
        return get_object_or_404(
            Program,
            pk=self.kwargs["program_pk"],
            created_by=self.request.user,
            is_deleted=False,
        )

    def get_queryset(self):
        program = self.get_program()

        return ProgramDay.objects.filter(
            program=program,
            is_deleted=False,
        ).prefetch_related(
            active_program_exercises(),
        )

    def perform_create(self, serializer):
        program = self.get_program()

        if program.program_type not in (
            Program.ProgramType.BODYBUILDING,
            Program.ProgramType.CORRECTIVE,
        ):
            raise ValidationError({
                "detail": (
                    "ایجاد جلسه فقط برای برنامه‌های "
                    "بدنسازی و اصلاحی مجاز است."
                )
            })

        serializer.save(
            program=program,
        )


# ---------------------------------------
# ProgramDay Detail + Update + Soft Delete
# GET / PATCH / DELETE
# ---------------------------------------

class ProgramDayDetailView(RetrieveUpdateDestroyAPIView):
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

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProgramDayListSerializer

        return ProgramDayCreateSerializer

    def get_queryset(self):
        return ProgramDay.objects.filter(
            program_id=self.kwargs["program_pk"],
            program__created_by=self.request.user,
            program__is_deleted=False,
            is_deleted=False,
        ).select_related(
            "program",
        ).prefetch_related(
            active_program_exercises(),
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
# ProgramDay Restore
# PATCH
# ---------------------------------------

class ProgramDayRestoreView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, program_pk, pk):
        program_day = get_object_or_404(
            ProgramDay.objects.select_related(
                "program",
            ).prefetch_related(
                active_program_exercises(),
            ),
            pk=pk,
            program_id=program_pk,
            program__created_by=request.user,
            program__is_deleted=False,
        )

        if not program_day.is_deleted:
            return Response(
                {
                    "detail": (
                        "این جلسه فعال است و "
                        "نیازی به بازیابی ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        program_day.is_deleted = False
        program_day.deleted_at = None

        program_day.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )

        serializer = ProgramDayListSerializer(
            program_day,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------
# Add Exercise to ProgramDay
# POST
# ---------------------------------------

class ProgramExerciseCreateView(CreateAPIView):
    serializer_class = ProgramExerciseCreateSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def perform_create(self, serializer):
        program_day = get_object_or_404(
            ProgramDay.objects.select_related("program"),
            pk=self.kwargs["day_pk"],
            program_id=self.kwargs["program_pk"],
            program__created_by=self.request.user,
            program__is_deleted=False,
            is_deleted=False,
        )

        program = program_day.program

        if program.program_type not in (
            Program.ProgramType.BODYBUILDING,
            Program.ProgramType.CORRECTIVE,
        ):
            raise ValidationError({
                "detail": (
                    "افزودن حرکت فقط برای برنامه‌های "
                    "بدنسازی و اصلاحی مجاز است."
                )
            })

        serializer.save(
            program_day=program_day,
        )


# ---------------------------------------
# ProgramExercise Detail + Update + Delete
# GET / PATCH / DELETE
# ---------------------------------------

class ProgramExerciseDetailView(
    RetrieveUpdateDestroyAPIView
):
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

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProgramExerciseReadSerializer

        return ProgramExerciseCreateSerializer

    def get_queryset(self):
        return ProgramExercise.objects.filter(
            program_day_id=self.kwargs["day_pk"],
            program_day__program_id=self.kwargs["program_pk"],
            program_day__program__created_by=self.request.user,
            program_day__program__is_deleted=False,
            program_day__is_deleted=False,
            is_deleted=False,
        ).select_related(
            "exercise",
            "program_day",
            "program_day__program",
        ).prefetch_related(
            "exercise__media",
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
# ProgramExercise Restore
# PATCH
# ---------------------------------------

class ProgramExerciseRestoreView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, program_pk, day_pk, pk):
        program_exercise = get_object_or_404(
            ProgramExercise.objects.select_related(
                "exercise",
                "program_day",
            ).prefetch_related(
                "exercise__media",
            ),
            pk=pk,
            program_day_id=day_pk,
            program_day__program_id=program_pk,
            program_day__program__created_by=request.user,
            program_day__program__is_deleted=False,
            program_day__is_deleted=False,
        )

        if not program_exercise.is_deleted:
            return Response(
                {
                    "detail": (
                        "این حرکت فعال است و "
                        "نیازی به بازیابی ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        program_exercise.is_deleted = False
        program_exercise.deleted_at = None

        program_exercise.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )

        serializer = ProgramExerciseReadSerializer(
            program_exercise,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )