from django.test import TestCase
from rest_framework.test import APITestCase

from orders.models import PurchaseOrder

from questionnaires.models import (
    QuestionnaireTemplate,
    ProgramQuestionnaire,
)
from accounts.models import User
from students.models import StudentProfile
from programs.models import Program
from questionnaires.models import (
    QuestionnaireTemplate,
    ProgramQuestionnaire,
)


class StudentProgramStatusTests(APITestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000201",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.student_user = User.objects.create_user(
            phone="09120000202",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student, _ = StudentProfile.objects.get_or_create(
            user=self.student_user,
        )

        other_user = User.objects.create_user(
            phone="09120000203",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        other_student, _ = StudentProfile.objects.get_or_create(
            user=other_user,
        )

        self.programs = {}

        # Create one program for every status.
        for program_status in Program.Status.values:
            program = Program.objects.create(
                student=self.student,
                created_by=self.coach,
                program_type=Program.ProgramType.BODYBUILDING,
                status=program_status,
            )

            self.programs[program_status] = program

        # Another student's program.
        self.other_program = Program.objects.create(
            student=other_student,
            created_by=self.coach,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.ACTIVE,
        )

        # Deleted programs must remain hidden.
        self.deleted_program = Program.objects.create(
            student=self.student,
            created_by=self.coach,
            program_type=Program.ProgramType.CORRECTIVE,
            status=Program.Status.ACTIVE,
            is_deleted=True,
        )

        self.client.force_authenticate(user=self.student_user)

        self.url = "/api/programs/my/"

    # TEST 1: All own statuses are visible.
    def test_student_sees_all_own_program_statuses(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        results = response.data["results"]

        program_ids = {item["id"] for item in results}

        expected_ids = {program.id for program in self.programs.values()}

        self.assertEqual(program_ids, expected_ids)

        self.assertNotIn(
            self.other_program.id,
            program_ids,
        )

        self.assertNotIn(
            self.deleted_program.id,
            program_ids,
        )

        for item in results:
            self.assertIn(
                "status_display",
                item,
            )

    # TEST 2: Status filtering works.
    def test_filter_programs_by_status(self):

        for program_status in Program.Status.values:
            with self.subTest(status=program_status):

                response = self.client.get(
                    self.url,
                    {"status": program_status},
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                results = response.data["results"]

                self.assertEqual(len(results), 1)

                self.assertEqual(
                    results[0]["status"],
                    program_status,
                )

        invalid_response = self.client.get(
            self.url,
            {"status": "INVALID"},
        )

        self.assertEqual(
            invalid_response.status_code,
            400,
        )

    # TEST 3: Unpublished details remain hidden.
    def test_unpublished_program_details_are_hidden(self):

        for program_status in (
            Program.Status.WAITING,
            Program.Status.PREPARING,
        ):
            with self.subTest(status=program_status):

                program = self.programs[program_status]

                response = self.client.get(f"/api/programs/my/{program.id}/")

                self.assertEqual(
                    response.status_code,
                    404,
                )


class StudentQuestionnaireSummaryTests(APITestCase):

    def test_questionnaire_status_appears_in_program_list(self):

        coach = User.objects.create_user(
            phone="09120000301",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        student_user = User.objects.create_user(
            phone="09120000302",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        student, _ = StudentProfile.objects.get_or_create(
            user=student_user,
        )

        template = QuestionnaireTemplate.objects.create(
            program_type=Program.ProgramType.BODYBUILDING,
            title="پرسش‌نامه بدنسازی",
        )

        # Program with a questionnaire.
        waiting_program = Program.objects.create(
            student=student,
            created_by=coach,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )

        ProgramQuestionnaire.objects.create(
            program=waiting_program,
            template=template,
            status=ProgramQuestionnaire.Status.DRAFT,
        )

        # Program without a questionnaire.
        preparing_program = Program.objects.create(
            student=student,
            created_by=coach,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.PREPARING,
        )

        self.client.force_authenticate(user=student_user)

        response = self.client.get("/api/programs/my/")

        self.assertEqual(response.status_code, 200)

        results = {item["id"]: item for item in response.data["results"]}

        self.assertEqual(
            results[waiting_program.id]["questionnaire_status"],
            "DRAFT",
        )

        self.assertEqual(
            results[waiting_program.id]["questionnaire_status_display"],
            "پیش‌نویس",
        )

        self.assertIsNone(results[preparing_program.id]["questionnaire_status"])

        self.assertIsNone(results[preparing_program.id]["questionnaire_status_display"])


class StudentGuidanceMessageTests(APITestCase):

    def test_student_receives_correct_guidance(self):

        coach = User.objects.create_user(
            phone="09120000401",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        user = User.objects.create_user(
            phone="09120000402",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        student, _ = StudentProfile.objects.get_or_create(
            user=user,
        )

        template = QuestionnaireTemplate.objects.create(
            program_type=Program.ProgramType.BODYBUILDING,
            title="پرسش‌نامه بدنسازی",
        )

        waiting_program = Program.objects.create(
            student=student,
            created_by=coach,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )

        ProgramQuestionnaire.objects.create(
            program=waiting_program,
            template=template,
            status=ProgramQuestionnaire.Status.DRAFT,
        )

        preparing_program = Program.objects.create(
            student=student,
            created_by=coach,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.PREPARING,
        )

        expired_program = Program.objects.create(
            student=student,
            created_by=coach,
            program_type=Program.ProgramType.CORRECTIVE,
            status=Program.Status.EXPIRED,
        )

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/programs/my/")

        self.assertEqual(response.status_code, 200)

        results = {item["id"]: item for item in response.data["results"]}

        self.assertEqual(
            results[waiting_program.id]["student_message"],
            "لطفاً پرسش‌نامه برنامه را تکمیل و ارسال کنید.",
        )

        self.assertEqual(
            results[preparing_program.id]["student_message"],
            "مربی در حال آماده‌سازی برنامه شماست.",
        )

        self.assertEqual(
            results[expired_program.id]["student_message"],
            ("دوره این برنامه پایان یافته و " "در آرشیو قابل مشاهده است."),
        )


class CoachDashboardTests(APITestCase):

    def setUp(self):

        self.coach1 = User.objects.create_user(
            phone="09120000601",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.coach2 = User.objects.create_user(
            phone="09120000602",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.students = []

        for phone in [
            "09120000603",
            "09120000604",
            "09120000605",
        ]:
            user = User.objects.create_user(
                phone=phone,
                password="TestPass123!",
                role=User.Role.STUDENT,
            )

            student, _ = StudentProfile.objects.get_or_create(
                user=user,
            )

            self.students.append(student)

        self.program1 = Program.objects.create(
            student=self.students[0],
            created_by=self.coach1,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )

        self.program2 = Program.objects.create(
            student=self.students[1],
            created_by=self.coach1,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.PREPARING,
        )

        self.program3 = Program.objects.create(
            student=self.students[2],
            created_by=self.coach2,
            program_type=Program.ProgramType.CORRECTIVE,
            status=Program.Status.ACTIVE,
        )

        template = QuestionnaireTemplate.objects.create(
            program_type=Program.ProgramType.NUTRITION,
            title="پرسش‌نامه تست تغذیه",
        )

        ProgramQuestionnaire.objects.create(
            program=self.program2,
            template=template,
            status=ProgramQuestionnaire.Status.SUBMITTED,
        )

        # Coach 1: successful purchases
        PurchaseOrder.objects.create(
            student=self.students[0],
            coach=self.coach1,
            program_type=Program.ProgramType.BODYBUILDING,
            amount_irr=1500000,
            status=PurchaseOrder.Status.PAID,
            program=self.program1,
            payment_reference="DASHBOARD-PAID-001",
        )

        PurchaseOrder.objects.create(
            student=self.students[1],
            coach=self.coach1,
            program_type=Program.ProgramType.NUTRITION,
            amount_irr=1200000,
            status=PurchaseOrder.Status.PAID,
            program=self.program2,
            payment_reference="DASHBOARD-PAID-002",
        )

        # Coach 1: unpaid purchase
        PurchaseOrder.objects.create(
            student=self.students[0],
            coach=self.coach1,
            program_type=Program.ProgramType.CORRECTIVE,
            amount_irr=1800000,
            status=PurchaseOrder.Status.PENDING,
        )

        # Coach 2: successful purchase
        PurchaseOrder.objects.create(
            student=self.students[2],
            coach=self.coach2,
            program_type=Program.ProgramType.CORRECTIVE,
            amount_irr=9000000,
            status=PurchaseOrder.Status.PAID,
            program=self.program3,
            payment_reference="DASHBOARD-PAID-003",
        )

        self.url = "/api/programs/coach/dashboard/"

    def test_coach_dashboard_statistics(self):

        self.client.force_authenticate(user=self.coach1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertEqual(
            data["students_count"],
            2,
        )

        self.assertEqual(
            data["programs"]["total"],
            2,
        )

        self.assertEqual(
            data["programs"]["waiting"],
            1,
        )

        self.assertEqual(
            data["programs"]["preparing"],
            1,
        )

        self.assertEqual(
            data["payments"]["paid_orders_count"],
            2,
        )

        self.assertEqual(
            data["payments"]["total_revenue_irr"],
            2700000,
        )

        self.assertEqual(
            data["actions"]["submitted_questionnaires_count"],
            1,
        )

        self.assertEqual(
            len(data["recent_paid_orders"]),
            2,
        )

    def test_coach_data_isolation(self):

        self.client.force_authenticate(user=self.coach2)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["students_count"],
            1,
        )

        self.assertEqual(
            response.data["programs"]["total"],
            1,
        )

        self.assertEqual(
            response.data["payments"]["total_revenue_irr"],
            9000000,
        )

        self.assertEqual(
            response.data["payments"]["paid_orders_count"],
            1,
        )

    def test_student_cannot_access_dashboard(self):

        self.client.force_authenticate(user=self.students[0].user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            403,
        )
