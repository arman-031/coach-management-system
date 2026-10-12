from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsCoach
from accounts.permissions import IsStudent
from programs.models import Program

from .models import (
    ProgramQuestionnaire,
    ProgramQuestionnaireItem,
)

from .serializers import (
    StudentQuestionnaireSerializer,
    QuestionnaireAnswerUpdateSerializer,
    CoachRevisionRequestSerializer,
)

class StudentQuestionnaireDetailView(RetrieveAPIView):

    serializer_class = StudentQuestionnaireSerializer

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    def get_object(self):

        program = get_object_or_404(
            Program,
            pk=self.kwargs["program_pk"],
            student__user=self.request.user,
            is_deleted=False,
        )

        questionnaire = get_object_or_404(
            ProgramQuestionnaire.objects.prefetch_related(
                "items",
            ),
            program=program,
        )

        self.check_object_permissions(
            self.request,
            questionnaire,
        )

        return questionnaire




class StudentQuestionnaireAnswerView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    @transaction.atomic
    def patch(self, request, program_pk, item_pk):

        questionnaire = get_object_or_404(
            ProgramQuestionnaire.objects.select_for_update(),
            program_id=program_pk,
            program__student__user=request.user,
            program__is_deleted=False,
        )

        if questionnaire.status not in (
            ProgramQuestionnaire.Status.NOT_STARTED,
            ProgramQuestionnaire.Status.DRAFT,
            ProgramQuestionnaire.Status.REVISION_REQUESTED,
        ):
            raise ValidationError({
                "detail": (
                    "ویرایش پاسخ‌های این پرسش‌نامه مجاز نیست."
                )
            })

        if questionnaire.program.status not in (
            Program.Status.WAITING,
            Program.Status.PREPARING,
        ):
            raise ValidationError({
                "detail": (
                    "ویرایش پرسش‌نامه برنامه منتشرشده "
                    "یا منقضی‌شده مجاز نیست."
                )
            })

        item = get_object_or_404(
            ProgramQuestionnaireItem,
            pk=item_pk,
            questionnaire=questionnaire,
        )

        serializer = QuestionnaireAnswerUpdateSerializer(
            data=request.data,
            context={"item": item},
        )

        serializer.is_valid(raise_exception=True)

        item.answer = serializer.validated_data["answer"]

        item.save(
            update_fields=[
                "answer",
                "updated_at",
            ]
        )

        # Keep revision status until the student resubmits.
        if questionnaire.status == (
            ProgramQuestionnaire.Status.NOT_STARTED
        ):
            questionnaire.status = (
                ProgramQuestionnaire.Status.DRAFT
            )

            questionnaire.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        elif questionnaire.status == (
            ProgramQuestionnaire.Status.DRAFT
        ):
            pass

        return Response(
            {
                "item_id": item.id,
                "answer": item.answer,
                "questionnaire_status": questionnaire.status,
                "detail": "پاسخ با موفقیت ذخیره شد.",
            }
        )



# ---------------------------------------
# Student Questionnaire Submit
# POST
# ---------------------------------------

class StudentQuestionnaireSubmitView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsStudent,
    ]

    @transaction.atomic
    def post(self, request, program_pk):

        # Find and lock the student's questionnaire.
        questionnaire = get_object_or_404(
            ProgramQuestionnaire.objects
            .select_related("program")
            .select_for_update(),

            program_id=program_pk,
            program__student__user=request.user,
            program__is_deleted=False,
        )

        # Check questionnaire status.
        allowed_statuses = (
            ProgramQuestionnaire.Status.NOT_STARTED,
            ProgramQuestionnaire.Status.DRAFT,
            ProgramQuestionnaire.Status.REVISION_REQUESTED,
        )

        if questionnaire.status not in allowed_statuses:
            return Response(
                {
                    "detail": "این پرسش‌نامه قبلاً ارسال نهایی شده است."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        program = questionnaire.program

        # Check program status.
        if program.status not in (
            Program.Status.WAITING,
            Program.Status.PREPARING,
        ):
            return Response(
                {
                    "detail": (
                        "ارسال پرسش‌نامه برای برنامه منتشرشده "
                        "یا منقضی‌شده مجاز نیست."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Load the saved questions and answers.
        items = list(
            questionnaire.items.all().order_by(
                "order",
                "id",
            )
        )

        if not items:
            return Response(
                {
                    "detail": "این پرسش‌نامه هیچ سؤالی ندارد."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate all saved answers.
        errors = {}

        for item in items:

            answer_serializer = (
                QuestionnaireAnswerUpdateSerializer(
                    data={"answer": item.answer},
                    context={"item": item},
                )
            )

            if not answer_serializer.is_valid():
                errors[str(item.id)] = (
                    answer_serializer.errors.get(
                        "answer",
                        ["پاسخ معتبر نیست."],
                    )
                )
                continue

            validated_answer = (
                answer_serializer.validated_data["answer"]
            )

            if item.is_required and validated_answer is None:
                errors[str(item.id)] = [
                    "پاسخ به این سؤال الزامی است."
                ]

        if errors:
            return Response(
                {
                    "detail": (
                        "لطفاً پاسخ سؤال‌های ناقص یا "
                        "نامعتبر را اصلاح کنید."
                    ),
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Submit the questionnaire.
        questionnaire.status = (
            ProgramQuestionnaire.Status.SUBMITTED
        )

        questionnaire.submitted_at = timezone.now()
        questionnaire.revision_reason = ""

        questionnaire.save(
            update_fields=[
                "status",
                "submitted_at",
                "revision_reason",
                "updated_at",
            ]
        )

        # Automatically start preparing the program.
        if program.status == Program.Status.WAITING:

            program.status = Program.Status.PREPARING

            program.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return Response(
            {
                "detail": (
                    "پرسش‌نامه با موفقیت ارسال شد "
                    "و برنامه آماده طراحی توسط مربی است."
                ),
                "questionnaire_id": questionnaire.id,
                "questionnaire_status": questionnaire.status,
                "program_id": program.id,
                "program_status": program.status,
                "submitted_at": questionnaire.submitted_at,
            },
            status=status.HTTP_200_OK,
        )


class CoachQuestionnaireDetailView(RetrieveAPIView):

    serializer_class = StudentQuestionnaireSerializer

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    def get_object(self):

        questionnaire = get_object_or_404(
            ProgramQuestionnaire.objects.prefetch_related(
                "items",
            ),
            program_id=self.kwargs["program_pk"],
            program__created_by=self.request.user,
            program__is_deleted=False,
        )

        self.check_object_permissions(
            self.request,
            questionnaire,
        )

        return questionnaire



class CoachQuestionnaireRevisionView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCoach,
    ]

    @transaction.atomic
    def post(self, request, program_pk):

        # Find and lock the coach's program.
        program = get_object_or_404(
            Program.objects.select_for_update(),
            pk=program_pk,
            created_by=request.user,
            is_deleted=False,
        )

        # Revisions are only allowed before publication.
        if program.status not in (
            Program.Status.WAITING,
            Program.Status.PREPARING,
        ):
            return Response(
                {
                    "detail": (
                        "برای برنامه منتشرشده یا منقضی‌شده "
                        "نمی‌توان درخواست اصلاح ثبت کرد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find and lock the questionnaire.
        questionnaire = get_object_or_404(
            ProgramQuestionnaire.objects.select_for_update(),
            program=program,
        )

        # The questionnaire must already be submitted.
        if questionnaire.status != (
            ProgramQuestionnaire.Status.SUBMITTED
        ):
            return Response(
                {
                    "detail": (
                        "درخواست اصلاح فقط برای پرسش‌نامه "
                        "ارسال نهایی‌شده مجاز است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CoachRevisionRequestSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        # Save the coach's revision request.
        questionnaire.status = (
            ProgramQuestionnaire.Status.REVISION_REQUESTED
        )

        questionnaire.revision_reason = (
            serializer.validated_data["reason"]
        )

        questionnaire.save(
            update_fields=[
                "status",
                "revision_reason",
                "updated_at",
            ]
        )

        return Response(
            {
                "detail": "درخواست اصلاح با موفقیت ثبت شد.",
                "program_id": program.id,
                "program_status": program.status,
                "questionnaire_status": questionnaire.status,
                "revision_reason": questionnaire.revision_reason,
            },
            status=status.HTTP_200_OK,
        )