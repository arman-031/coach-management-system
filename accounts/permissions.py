from rest_framework.permissions import BasePermission

from .models import User


class IsCoach(BasePermission):
    message = "فقط مربی اجازه دسترسی به این بخش را دارد."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.COACH
        )


class IsStudent(BasePermission):
    message = "فقط شاگرد اجازه دسترسی به این بخش را دارد."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.STUDENT
        )