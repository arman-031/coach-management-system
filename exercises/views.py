from rest_framework.generics import ListAPIView ,CreateAPIView,RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsCoach
from .models import Exercise, MuscleGroup
from .serializers import ExerciseListSerializer,ExerciseCreateSerializer,MuscleGroupSerializer,ExerciseUpdateSerializer
from rest_framework.parsers import (FormParser,MultiPartParser)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class ExerciseListView(ListAPIView):
    serializer_class = ExerciseListSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    filterset_fields = (
        "is_system",
        "is_active",
        "difficulty",
        "primary_muscle",
    )

    search_fields = (
        "name",
        "description",
        "primary_muscle__name",
    )

    ordering_fields = (
        "name",
        "created_at",
    )

    ordering = ("name",)

    def get_queryset(self):
        return Exercise.objects.select_related(
            "primary_muscle",
        ).prefetch_related(
             "media",
        ).filter(
             is_active=True,
        )


class ExerciseCreateView(CreateAPIView):
    serializer_class = ExerciseCreateSerializer
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            is_system=False,
            is_active=True,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        self.perform_create(
            serializer
        )

        exercise = serializer.instance

        output_serializer = ExerciseListSerializer(
            exercise,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )

class MuscleGroupListView(ListAPIView):
    serializer_class = MuscleGroupSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    def get_queryset(self):
        return MuscleGroup.objects.filter(
            is_active=True,
        ).order_by("name")




class ExerciseUpdateView(RetrieveUpdateAPIView):
    serializer_class = ExerciseUpdateSerializer
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_queryset(self):
        return Exercise.objects.filter(
            is_system=False,
        )

    def perform_update(self, serializer):
        exercise = self.get_object()

        if exercise.is_system:
            raise PermissionDenied(
                "حرکت‌های سیستمی قابل ویرایش مستقیم نیستند."
            )

        serializer.save()


class ExerciseDeactivateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        try:
            exercise = Exercise.objects.get(
                pk=pk,
                is_system=False,
            )
        except Exercise.DoesNotExist:
            return Response(
                {
                    "detail": "حرکت اختصاصی پیدا نشد."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        exercise.is_active = False

        exercise.save(
            update_fields=["is_active"]
        )

        return Response(
            {
                "detail": "حرکت با موفقیت غیرفعال شد."
            },
            status=status.HTTP_200_OK,
        )


class ExerciseActivateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        try:
            exercise = Exercise.objects.get(
                pk=pk,
                is_system=False,
            )
        except Exercise.DoesNotExist:
            return Response(
                {
                    "detail": "حرکت اختصاصی پیدا نشد."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        exercise.is_active = True

        exercise.save(
            update_fields=["is_active"]
        )

        return Response(
            {
                "detail": "حرکت با موفقیت فعال شد."
            },
            status=status.HTTP_200_OK,
        )