from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCoach

from .models import Exercise, ExerciseMedia, MuscleGroup
from .serializers import (
    ExerciseCreateSerializer,
    ExerciseDetailSerializer,
    ExerciseListSerializer,
    ExerciseMediaCreateSerializer,
    ExerciseMediaUpdateSerializer,
    ExerciseUpdateSerializer,
    MuscleGroupSerializer,
)


def _owned_custom_exercises(user):
    return Exercise.objects.filter(
        is_system=False,
        created_by=user,
    )


def _owned_custom_media(user, exercise_id):
    return ExerciseMedia.objects.filter(
        exercise_id=exercise_id,
        exercise__is_system=False,
        exercise__created_by=user,
    )


class ExerciseListView(ListAPIView):
    serializer_class = ExerciseListSerializer
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

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
            Prefetch(
                "media",
                queryset=ExerciseMedia.objects.filter(
                    is_primary=True,
                ).order_by(
                    "order",
                    "id",
                ),
                to_attr="primary_media_items",
            )
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
        return _owned_custom_exercises(self.request.user)


class ExerciseStatusView(APIView):
    is_active = None
    success_message = ""

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        try:
            exercise = _owned_custom_exercises(request.user).get(pk=pk)
        except Exercise.DoesNotExist:
            return Response(
                {"detail": "حرکت اختصاصی پیدا نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        exercise.is_active = self.is_active
        exercise.save(update_fields=["is_active"])

        return Response(
            {"detail": self.success_message},
            status=status.HTTP_200_OK,
        )


class ExerciseDeactivateView(ExerciseStatusView):
    is_active = False
    success_message = "حرکت با موفقیت غیرفعال شد."


class ExerciseActivateView(ExerciseStatusView):
    is_active = True
    success_message = "حرکت با موفقیت فعال شد."


class ExerciseCopyView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def post(self, request, pk):
        try:
            source_exercise = Exercise.objects.get(
                pk=pk,
                is_system=True,
                is_active=True,
            )
        except Exercise.DoesNotExist:
            return Response(
                {"detail": "حرکت سیستمی پیدا نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        copied_exercise = Exercise.objects.create(
            name=f"{source_exercise.name} - نسخه مربی",
            description=source_exercise.description,
            equipment=source_exercise.equipment,
            common_mistake=source_exercise.common_mistake,
            primary_muscle=source_exercise.primary_muscle,
            difficulty=source_exercise.difficulty,
            is_system=False,
            created_by=request.user,
            copied_from=source_exercise,
            is_active=True,
        )
        copied_exercise.secondary_muscles.set(
            source_exercise.secondary_muscles.all()
        )

        output_serializer = ExerciseListSerializer(
            copied_exercise,
            context={"request": request},
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ExerciseMediaCreateView(CreateAPIView):
    serializer_class = ExerciseMediaCreateSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def perform_create(self, serializer):
        try:
            exercise = _owned_custom_exercises(
                self.request.user
            ).get(pk=self.kwargs["pk"])
        except Exercise.DoesNotExist as exc:
            raise PermissionDenied(
                "این حرکت اختصاصی پیدا نشد یا اجازه ویرایش آن را ندارید."
            ) from exc

        serializer.save(
            exercise=exercise
        )


class ExerciseMediaUpdateView(RetrieveUpdateAPIView):
    serializer_class = ExerciseMediaUpdateSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self):
        return _owned_custom_media(
            self.request.user,
            self.kwargs["exercise_pk"],
        )


class ExerciseMediaDeleteView(DestroyAPIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_queryset(self):
        return _owned_custom_media(
            self.request.user,
            self.kwargs["exercise_pk"],
        )

    def perform_destroy(self, instance):
        exercise = instance.exercise

        was_primary = instance.is_primary

        file_name = (
            instance.file.name
            if instance.file
            else None
        )

        thumbnail_name = (
            instance.thumbnail.name
            if instance.thumbnail
            else None
        )

        file_storage = (
            instance.file.storage
            if instance.file
            else None
        )

        thumbnail_storage = (
            instance.thumbnail.storage
            if instance.thumbnail
            else None
        )

        instance.delete()

        if file_name and file_storage:
            file_storage.delete(file_name)

        if thumbnail_name and thumbnail_storage:
            thumbnail_storage.delete(
                thumbnail_name
            )

        if was_primary:
            next_media = exercise.media.order_by(
                "order",
                "id",
            ).first()

            if next_media:
                next_media.is_primary = True
                next_media.save(
                    update_fields=["is_primary"]
                )


class ExerciseDetailView(RetrieveAPIView):
    serializer_class = ExerciseDetailSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_queryset(self):
        return Exercise.objects.filter(
            Q(is_system=True)
            | Q(created_by=self.request.user)
        ).select_related(
            "primary_muscle",
            "copied_from",
        ).prefetch_related(
            "secondary_muscles",
            "media",
        )
