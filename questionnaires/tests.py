from datetime import timedelta
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from students.models import StudentProfile
from programs.models import (
    NutritionDay,
    NutritionFoodItem,
    NutritionMeal,
    Program,
)

from questionnaires.models import (
    QuestionnaireTemplate,
    TemplateQuestion,
    ProgramQuestionnaire,
)

from questionnaires.services import (
    initialize_program_questionnaire,
)


class StudentQuestionnaireFlowTests(APITestCase):

    def setUp(self):

        # Create coach.
        self.coach = User.objects.create_user(
            phone="09120000501",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        # Create student.
        self.student_user = User.objects.create_user(
            phone="09120000502",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student, _ = StudentProfile.objects.get_or_create(
            user=self.student_user,
        )

        # Create an active questionnaire template.
        template = QuestionnaireTemplate.objects.create(
            program_type=Program.ProgramType.BODYBUILDING,
            title="پرسش‌نامه اولیه بدنسازی",
        )

        TemplateQuestion.objects.create(
            template=template,
            text="هدف شما از تمرین چیست؟",
            answer_type=TemplateQuestion.AnswerType.SHORT_TEXT,
            is_required=True,
            order=1,
        )

        # Simulate a purchased program waiting
        # for its initial questionnaire.
        self.program = Program.objects.create(
            student=self.student,
            created_by=self.coach,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )

        self.questionnaire = initialize_program_questionnaire(self.program.id)

        self.item = self.questionnaire.items.get()

        self.client.force_authenticate(user=self.student_user)

    def test_questionnaire_completion_flow(self):

        base_url = f"/api/programs/my/{self.program.id}/questionnaire/"

        # Step 1: Student views the questionnaire.
        detail_response = self.client.get(base_url)

        self.assertEqual(
            detail_response.status_code,
            200,
        )

        self.assertEqual(
            detail_response.data["status"],
            ProgramQuestionnaire.Status.NOT_STARTED,
        )

        self.assertEqual(
            len(detail_response.data["items"]),
            1,
        )

        # Step 2: Submitting without answers is rejected.
        incomplete_response = self.client.post(
            f"{base_url}submit/",
            format="json",
        )

        self.assertEqual(
            incomplete_response.status_code,
            400,
        )

        self.program.refresh_from_db()

        self.assertEqual(
            self.program.status,
            Program.Status.WAITING,
        )

        # Step 3: Student saves an answer.
        answer_url = f"{base_url}items/{self.item.id}/answer/"

        answer_response = self.client.patch(
            answer_url,
            {"answer": "افزایش قدرت و عضله‌سازی"},
            format="json",
        )

        self.assertEqual(
            answer_response.status_code,
            200,
        )

        self.item.refresh_from_db()
        self.questionnaire.refresh_from_db()

        self.assertEqual(
            self.item.answer,
            "افزایش قدرت و عضله‌سازی",
        )

        self.assertEqual(
            self.questionnaire.status,
            ProgramQuestionnaire.Status.DRAFT,
        )

        # Step 4: Student submits the questionnaire.
        submit_response = self.client.post(
            f"{base_url}submit/",
            format="json",
        )

        self.assertEqual(
            submit_response.status_code,
            200,
        )

        self.questionnaire.refresh_from_db()
        self.program.refresh_from_db()

        self.assertEqual(
            self.questionnaire.status,
            ProgramQuestionnaire.Status.SUBMITTED,
        )

        self.assertIsNotNone(self.questionnaire.submitted_at)

        # Program automatically moves to PREPARING.
        self.assertEqual(
            self.program.status,
            Program.Status.PREPARING,
        )

        # The 45-day countdown has not started.
        self.assertIsNone(self.program.published_at)

        self.assertIsNone(self.program.expires_at)

        # Step 5: Repeated submission is rejected.
        repeated_response = self.client.post(
            f"{base_url}submit/",
            format="json",
        )

        self.assertEqual(
            repeated_response.status_code,
            400,
        )

        # Step 6: Answers cannot change after submission.
        edit_response = self.client.patch(
            answer_url,
            {"answer": "پاسخ جدید"},
            format="json",
        )

        self.assertEqual(
            edit_response.status_code,
            400,
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.answer,
            "افزایش قدرت و عضله‌سازی",
        )

    def test_coach_can_request_revision_and_review_resubmission(self):
        base_url = f"/api/programs/my/{self.program.id}/questionnaire/"
        answer_url = f"{base_url}items/{self.item.id}/answer/"

        self.client.patch(
            answer_url,
            {"answer": "افزایش قدرت"},
            format="json",
        )
        self.client.post(f"{base_url}submit/", format="json")

        self.client.force_authenticate(user=self.coach)
        coach_url = f"/api/programs/{self.program.id}/questionnaire/"

        review_response = self.client.get(coach_url)

        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(
            review_response.data["items"][0]["answer"],
            "افزایش قدرت",
        )

        revision_url = (
            f"/api/programs/{self.program.id}/questionnaire/"
            "request-revision/"
        )
        invalid_revision_response = self.client.post(
            revision_url,
            {"reason": "کم"},
            format="json",
        )

        self.assertEqual(invalid_revision_response.status_code, 400)

        revision_response = self.client.post(
            revision_url,
            {"reason": "لطفاً هدف تمرین را دقیق‌تر توضیح دهید."},
            format="json",
        )

        self.assertEqual(revision_response.status_code, 200)
        self.assertEqual(
            revision_response.data["questionnaire_status"],
            ProgramQuestionnaire.Status.REVISION_REQUESTED,
        )

        self.client.force_authenticate(user=self.student_user)
        edit_response = self.client.patch(
            answer_url,
            {"answer": "افزایش قدرت و بهبود استقامت"},
            format="json",
        )

        self.assertEqual(edit_response.status_code, 200)
        self.assertEqual(
            edit_response.data["questionnaire_status"],
            ProgramQuestionnaire.Status.REVISION_REQUESTED,
        )

        resubmission_response = self.client.post(
            f"{base_url}submit/",
            format="json",
        )

        self.assertEqual(resubmission_response.status_code, 200)
        self.questionnaire.refresh_from_db()
        self.item.refresh_from_db()
        self.program.refresh_from_db()

        self.assertEqual(
            self.questionnaire.status,
            ProgramQuestionnaire.Status.SUBMITTED,
        )
        self.assertEqual(self.questionnaire.revision_reason, "")
        self.assertEqual(
            self.item.answer,
            "افزایش قدرت و بهبود استقامت",
        )
        self.assertEqual(self.program.status, Program.Status.PREPARING)
        self.assertIsNone(self.program.published_at)
        self.assertIsNone(self.program.expires_at)

        self.client.force_authenticate(user=self.coach)
        corrected_review_response = self.client.get(
            f"/api/programs/{self.program.id}/questionnaire/",
        )

        self.assertEqual(corrected_review_response.status_code, 200)
        self.assertEqual(
            corrected_review_response.data["status"],
            ProgramQuestionnaire.Status.SUBMITTED,
        )
        self.assertEqual(
            corrected_review_response.data["items"][0]["answer"],
            "افزایش قدرت و بهبود استقامت",
        )

    def test_student_and_coach_cannot_access_another_owners_questionnaire(self):
        other_student_user = User.objects.create_user(
            phone="09120000503",
            password="test-password",
            role=User.Role.STUDENT,
        )
        other_student, _ = StudentProfile.objects.get_or_create(
            user=other_student_user,
        )
        other_program = Program.objects.create(
            student=other_student,
            created_by=self.coach,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )
        initialize_program_questionnaire(other_program.id)

        student_questionnaire_url = (
            f"/api/programs/my/{self.program.id}/questionnaire/"
        )
        student_answer_url = (
            f"{student_questionnaire_url}items/{self.item.id}/answer/"
        )

        self.client.force_authenticate(user=other_student_user)
        self.assertEqual(
            self.client.get(student_questionnaire_url).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                student_answer_url,
                {"answer": "نباید ذخیره شود"},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"{student_questionnaire_url}submit/",
                format="json",
            ).status_code,
            404,
        )

        other_coach = User.objects.create_user(
            phone="09120000504",
            password="test-password",
            role=User.Role.COACH,
        )
        self.client.force_authenticate(user=other_coach)
        coach_questionnaire_url = (
            f"/api/programs/{self.program.id}/questionnaire/"
        )

        self.assertEqual(
            self.client.get(coach_questionnaire_url).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"{coach_questionnaire_url}request-revision/",
                {"reason": "لطفاً پاسخ را اصلاح کنید."},
                format="json",
            ).status_code,
            404,
        )

    def test_renewal_does_not_require_a_new_questionnaire(self):
        self.questionnaire.status = ProgramQuestionnaire.Status.SUBMITTED
        self.questionnaire.save(update_fields=["status"])

        renewal_program = Program.objects.create(
            student=self.student,
            created_by=self.coach,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )

        renewal_questionnaire = initialize_program_questionnaire(
            renewal_program.id,
        )
        renewal_program.refresh_from_db()

        self.assertIsNone(renewal_questionnaire)
        self.assertEqual(renewal_program.status, Program.Status.PREPARING)
        self.assertFalse(
            ProgramQuestionnaire.objects.filter(
                program=renewal_program,
            ).exists()
        )
        self.assertIsNone(renewal_program.published_at)
        self.assertIsNone(renewal_program.expires_at)

    def test_subscription_starts_only_when_coach_publishes(self):
        template = QuestionnaireTemplate.objects.create(
            program_type=Program.ProgramType.NUTRITION,
            title="پرسش‌نامه تغذیه",
        )
        question = TemplateQuestion.objects.create(
            template=template,
            text="هدف شما از برنامه تغذیه چیست؟",
            answer_type=TemplateQuestion.AnswerType.SHORT_TEXT,
            is_required=True,
            order=1,
        )
        program = Program.objects.create(
            student=self.student,
            created_by=self.coach,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.WAITING,
        )
        questionnaire = initialize_program_questionnaire(program.id)
        item = questionnaire.items.get(source_question=question)
        base_url = f"/api/programs/my/{program.id}/questionnaire/"

        self.client.patch(
            f"{base_url}items/{item.id}/answer/",
            {"answer": "بهبود عادت‌های غذایی"},
            format="json",
        )
        submission_response = self.client.post(
            f"{base_url}submit/",
            format="json",
        )

        self.assertEqual(submission_response.status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.status, Program.Status.PREPARING)
        self.assertIsNone(program.published_at)
        self.assertIsNone(program.expires_at)

        day = NutritionDay.objects.create(
            program=program,
            title="روز اول",
        )
        meal = NutritionMeal.objects.create(
            nutrition_day=day,
            title="صبحانه",
        )
        NutritionFoodItem.objects.create(
            nutrition_meal=meal,
            name="نان",
            quantity=Decimal("100"),
            unit=NutritionFoodItem.Unit.GRAM,
        )

        self.client.force_authenticate(user=self.coach)
        publish_response = self.client.patch(
            f"/api/programs/{program.id}/publish/",
            {},
            format="json",
        )

        self.assertEqual(publish_response.status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.status, Program.Status.ACTIVE)
        self.assertIsNotNone(program.published_at)
        self.assertEqual(
            program.expires_at,
            program.published_at + timedelta(days=program.duration_days),
        )
