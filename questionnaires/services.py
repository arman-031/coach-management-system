

from copy import deepcopy

from django.db import transaction
from django.core.exceptions import ValidationError

from programs.models import Program

from .models import (
    QuestionnaireTemplate,
    TemplateQuestion,
    ProgramQuestionnaire,
    ProgramQuestionnaireItem,
)


@transaction.atomic
def initialize_program_questionnaire(program_id):
    """
    Decide whether a program needs an initial questionnaire.

    Returns:
        ProgramQuestionnaire or None
    """

    # Lock the program during initialization.
    program = Program.objects.select_for_update().get(
        pk=program_id,
        is_deleted=False,
    )

    # Only initialize programs that are waiting.
    if program.status != Program.Status.WAITING:
        raise ValidationError(
            "فقط برنامه در انتظار قابل مقداردهی اولیه است."
        )

    # Avoid creating another questionnaire for the same program.
    existing = ProgramQuestionnaire.objects.filter(
        program=program,
    ).first()

    if existing:
        return existing

    # Has this student previously submitted a questionnaire
    # for the same program type?
    has_previous_answers = ProgramQuestionnaire.objects.filter(
        program__student=program.student,
        program__program_type=program.program_type,
        program__is_deleted=False,
        assignment_type=ProgramQuestionnaire.AssignmentType.INITIAL,
        status=ProgramQuestionnaire.Status.SUBMITTED,
    ).exclude(
        program=program,
    ).exists()

    if has_previous_answers:
        # Renewal: no repeated questionnaire required.
        program.status = Program.Status.PREPARING

        program.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return None

    # First questionnaire of this program type.
    template = QuestionnaireTemplate.objects.filter(
        program_type=program.program_type,
        is_active=True,
    ).first()

    if template is None:
        raise ValidationError(
            "قالب فعال پرسش‌نامه برای این نوع برنامه وجود ندارد."
        )

    questions = list(
        TemplateQuestion.objects.filter(
            template=template,
            is_active=True,
        ).order_by("order", "id")
    )

    if not questions:
        raise ValidationError(
            "قالب پرسش‌نامه هیچ سؤال فعالی ندارد."
        )

    questionnaire = ProgramQuestionnaire.objects.create(
        program=program,
        template=template,
        assignment_type=(
            ProgramQuestionnaire.AssignmentType.INITIAL
        ),
    )

    # Copy a snapshot of all active template questions.
    items = [
        ProgramQuestionnaireItem(
            questionnaire=questionnaire,
            source_question=question,
            question_key=question.key,
            text=question.text,
            answer_type=question.answer_type,
            options=deepcopy(question.options),
            is_required=question.is_required,
            order=question.order,
        )
        for question in questions
    ]

    ProgramQuestionnaireItem.objects.bulk_create(items)

    return questionnaire



@transaction.atomic
def request_additional_questionnaire(
    *,
    program_id,
    coach,
    question_ids,
):
    # Validate selected question IDs.
    if (
        not isinstance(question_ids, list)
        or not question_ids
        or any(
            type(question_id) is not int or question_id <= 0
            for question_id in question_ids
        )
        or len(question_ids) != len(set(question_ids))
    ):
        raise ValidationError(
            "باید یک یا چند شناسه سؤال معتبر و غیرتکراری ارسال شود."
        )

    # Find and lock the coach's program.
    program = Program.objects.select_for_update().get(
        pk=program_id,
        created_by=coach,
        is_deleted=False,
    )

    # Additional questionnaires are for preparing programs.
    if program.status != Program.Status.PREPARING:
        raise ValidationError(
            "درخواست سؤال تکمیلی فقط برای برنامه در حال آماده‌سازی مجاز است."
        )

    # One questionnaire per program.
    if ProgramQuestionnaire.objects.filter(
        program=program,
    ).exists():
        raise ValidationError(
            "این برنامه قبلاً پرسش‌نامه دریافت کرده است."
        )

    # Confirm the student completed the initial questionnaire
    # for this program type on an earlier program.
    has_initial_submission = ProgramQuestionnaire.objects.filter(
        program__student_id=program.student_id,
        program__program_type=program.program_type,
        program__is_deleted=False,
        assignment_type=ProgramQuestionnaire.AssignmentType.INITIAL,
        status=ProgramQuestionnaire.Status.SUBMITTED,
    ).exclude(
        program_id=program.id,
    ).exists()

    if not has_initial_submission:
        raise ValidationError(
            "پرسش‌نامه اولیه این نوع برنامه هنوز تکمیل نشده است."
        )

    # Find the matching active template.
    template = QuestionnaireTemplate.objects.filter(
        program_type=program.program_type,
        is_active=True,
    ).first()

    if template is None:
        raise ValidationError(
            "قالب فعال پرسش‌نامه پیدا نشد."
        )

    # Load only the questions selected by the coach.
    questions = list(
        TemplateQuestion.objects.filter(
            template=template,
            is_active=True,
            id__in=question_ids,
        ).order_by("order", "id")
    )

    if len(questions) != len(question_ids):
        raise ValidationError(
            "یک یا چند سؤال انتخاب‌شده معتبر یا فعال نیستند."
        )

    # Create the questionnaire.
    questionnaire = ProgramQuestionnaire.objects.create(
        program=program,
        template=template,
        assignment_type=(
            ProgramQuestionnaire.AssignmentType.COACH_REQUEST
        ),
    )

    # Save a snapshot of selected questions.
    items = [
        ProgramQuestionnaireItem(
            questionnaire=questionnaire,
            source_question=question,
            question_key=question.key,
            text=question.text,
            answer_type=question.answer_type,
            options=deepcopy(question.options),
            is_required=question.is_required,
            order=question.order,
        )
        for question in questions
    ]

    ProgramQuestionnaireItem.objects.bulk_create(items)

    return questionnaire