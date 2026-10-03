from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView,RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from accounts.models import User
from accounts.permissions import IsCoach, IsStudent
from .serializers import StudentListSerializer, StudentProfileSerializer,StudentDetailSerializer,StudentUpdateSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

class StudentProfileView(RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated,IsStudent]

    def get_object(self):
        return self.request.user.student_profile

    def get_object(self):
        return self.request.user.student_profile


class StudentListView(ListAPIView):
    serializer_class = StudentListSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    filterset_fields = (
        "is_active",
    )

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
        return User.objects.filter(
            role=User.Role.STUDENT,
        )


class StudentDetailView(RetrieveAPIView):
    serializer_class = StudentDetailSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    def get_queryset(self):
        return User.objects.filter(
            role=User.Role.STUDENT,
        ).select_related("student_profile")


class StudentDeactivateView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, pk):
        try:
            student = User.objects.get(
                pk=pk,
                role=User.Role.STUDENT,
            )
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "شاگرد موردنظر پیدا نشد."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        student.is_active = False
        student.save(update_fields=["is_active"])

        return Response(
            {
                "detail": "شاگرد با موفقیت غیرفعال شد."
            },
            status=status.HTTP_200_OK,
        )

class StudentActivateView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def patch(self, request, pk):
        try:
            student = User.objects.get(
                pk=pk,
                role=User.Role.STUDENT,
            )
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "شاگرد موردنظر پیدا نشد."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        student.is_active = True
        student.save(update_fields=["is_active"])

        return Response(
            {
                "detail": "شاگرد با موفقیت فعال شد."
            },
            status=status.HTTP_200_OK,
        )

class StudentUpdateView(RetrieveUpdateAPIView):
    serializer_class = StudentUpdateSerializer
    permission_classes = [IsAuthenticated, IsCoach]

    def get_queryset(self):
        return User.objects.filter(
            role=User.Role.STUDENT,
        )