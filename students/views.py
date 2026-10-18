from django.shortcuts import get_object_or_404

from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from accounts.permissions import IsCoach, IsStudent

from .access import coach_student_users
from .serializers import (
    StudentListSerializer,
    StudentProfileSerializer,
    StudentDetailSerializer,
    StudentUpdateSerializer,
)

# ==========================================
# Student: Own Profile
# ==========================================


class StudentProfileView(RetrieveUpdateAPIView):

    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_object(self):
        return self.request.user.student_profile


# ==========================================
# Coach: Student List
# ==========================================


class StudentListView(ListAPIView):

    serializer_class = StudentListSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    filterset_fields = ("is_active",)

    search_fields = (
        "phone",
        "first_name",
        "last_name",
        "email",
    )

    ordering_fields = (
        "created_at",
        "first_name",
        "last_name",
    )

    ordering = ("-created_at",)

    def get_queryset(self):
        return coach_student_users(self.request.user)


# ==========================================
# Coach: Student Detail
# ==========================================


class StudentDetailView(RetrieveAPIView):

    serializer_class = StudentDetailSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    def get_queryset(self):
        return coach_student_users(self.request.user).select_related("student_profile")


# ==========================================
# Coach: Deactivate Student
# ==========================================


class StudentDeactivateView(APIView):

    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, pk):

        student = get_object_or_404(
            coach_student_users(request.user),
            pk=pk,
        )

        student.is_active = False
        student.save(update_fields=["is_active"])

        return Response(
            {"detail": "شاگرد با موفقیت غیرفعال شد."},
            status=status.HTTP_200_OK,
        )


# ==========================================
# Coach: Activate Student
# ==========================================


class StudentActivateView(APIView):

    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, pk):

        student = get_object_or_404(
            coach_student_users(request.user),
            pk=pk,
        )

        student.is_active = True
        student.save(update_fields=["is_active"])

        return Response(
            {"detail": "شاگرد با موفقیت فعال شد."},
            status=status.HTTP_200_OK,
        )


# ==========================================
# Coach: Update Student
# ==========================================


class StudentUpdateView(RetrieveUpdateAPIView):

    serializer_class = StudentUpdateSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    def get_queryset(self):
        return coach_student_users(self.request.user)
