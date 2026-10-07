from rest_framework.generics import ListAPIView,RetrieveAPIView,CreateAPIView
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsCoach
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Program
from .serializers import ProgramListSerializer,ProgramDetailSerializer,ProgramCreateSerializer
from datetime import timedelta
from django.utils import timezone
from .services import expire_due_programs



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

    ordering = (
        "-created_at",
    )

    def get_queryset(self):
        expire_due_programs()

        return Program.objects.filter(
            created_by=self.request.user,
        ).select_related(
            "student",
            "student__user",
            "created_by",
        )


class ProgramDetailView(RetrieveAPIView):
    serializer_class = ProgramDetailSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_queryset(self):
        expire_due_programs()

        return Program.objects.filter(
            created_by=self.request.user,
        ).select_related(
            "student",
            "student__user",
            "created_by",
        )


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


class ProgramStartPreparingView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        try:
            program = Program.objects.get(
                pk=pk,
                created_by=request.user,
            )
        except Program.DoesNotExist:
            return Response(
                {
                    "detail": "برنامه پیدا نشد.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if program.status != Program.Status.WAITING:
            return Response(
                {
                    "detail": "فقط برنامه در انتظار را می‌توان وارد مرحله آماده‌سازی کرد.",
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
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class ProgramPublishView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def patch(self, request, pk):
        try:
            program = Program.objects.get(
                pk=pk,
                created_by=request.user,
            )
        except Program.DoesNotExist:
            return Response(
                {
                    "detail": "برنامه پیدا نشد.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if program.status != Program.Status.PREPARING:
            return Response(
                {
                    "detail": "فقط برنامه در حال آماده‌سازی را می‌توان منتشر کرد.",
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
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )