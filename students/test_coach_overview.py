from rest_framework.test import APITestCase

from accounts.models import User
from students.models import StudentProfile
from programs.models import Program
from orders.models import PurchaseOrder


class CoachStudentOverviewTests(APITestCase):

    def setUp(self):
        # Two coaches
        self.coach1 = User.objects.create_user(
            phone="09120000701",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.coach2 = User.objects.create_user(
            phone="09120000702",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        # Two students
        self.user1 = User.objects.create_user(
            phone="09120000703",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.user2 = User.objects.create_user(
            phone="09120000704",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student1, _ = StudentProfile.objects.get_or_create(user=self.user1)

        self.student2, _ = StudentProfile.objects.get_or_create(user=self.user2)

        # Programs belonging to different coaches
        self.program1 = Program.objects.create(
            student=self.student1,
            created_by=self.coach1,
            program_type=Program.ProgramType.BODYBUILDING,
            status=Program.Status.WAITING,
        )

        self.program2 = Program.objects.create(
            student=self.student1,
            created_by=self.coach2,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.PREPARING,
        )

        Program.objects.create(
            student=self.student2,
            created_by=self.coach2,
            program_type=Program.ProgramType.CORRECTIVE,
        )

        # Successful payment for coach 1
        self.paid_order1 = PurchaseOrder.objects.create(
            student=self.student1,
            coach=self.coach1,
            program_type=Program.ProgramType.BODYBUILDING,
            amount_irr=1500000,
            status=PurchaseOrder.Status.PAID,
            program=self.program1,
            payment_reference="OVERVIEW-TEST-001",
        )

        # Unpaid order for coach 1
        PurchaseOrder.objects.create(
            student=self.student1,
            coach=self.coach1,
            program_type=Program.ProgramType.CORRECTIVE,
            amount_irr=1800000,
            status=PurchaseOrder.Status.PENDING,
        )

        # Successful payment for coach 2
        PurchaseOrder.objects.create(
            student=self.student1,
            coach=self.coach2,
            program_type=Program.ProgramType.NUTRITION,
            amount_irr=9000000,
            status=PurchaseOrder.Status.PAID,
            program=self.program2,
            payment_reference="OVERVIEW-TEST-002",
        )

        self.url = f"/api/students/{self.user1.id}/overview/"

    def test_coach_sees_own_student_records(self):
        self.client.force_authenticate(user=self.coach1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertEqual(data["student"]["id"], self.user1.id)
        self.assertEqual(data["program_counts"]["total"], 1)
        self.assertEqual(data["program_counts"]["waiting"], 1)
        self.assertEqual(
            data["recent_programs"][0]["id"],
            self.program1.id,
        )

        self.assertEqual(data["orders"]["total"], 2)
        self.assertEqual(data["orders"]["paid"], 1)

        # Pending payments must not count as revenue.
        self.assertEqual(
            data["orders"]["total_revenue_irr"],
            1500000,
        )

    def test_second_coach_sees_only_own_records(self):
        self.client.force_authenticate(user=self.coach2)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["program_counts"]["total"],
            1,
        )

        self.assertEqual(
            response.data["recent_programs"][0]["id"],
            self.program2.id,
        )

        self.assertEqual(
            response.data["orders"]["total_revenue_irr"],
            9000000,
        )

    def test_unrelated_student_is_hidden(self):
        self.client.force_authenticate(user=self.coach1)

        other_url = f"/api/students/{self.user2.id}/overview/"

        response = self.client.get(other_url)
        self.assertEqual(response.status_code, 404)

        # Old student-management endpoints must be safe too.
        response = self.client.patch(f"/api/students/{self.user2.id}/deactivate/")

        self.assertEqual(response.status_code, 404)

        self.user2.refresh_from_db()
        self.assertTrue(self.user2.is_active)

    def test_student_cannot_access_coach_overview(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_coach_order_history_and_filters(self):

        self.client.force_authenticate(user=self.coach1)

        url = f"/api/students/{self.user1.id}/orders/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        statuses = {item["status"] for item in response.data["results"]}

        self.assertEqual(
            statuses,
            {"PAID", "PENDING"},
        )

        # Filter only paid orders.
        paid_response = self.client.get(
            url,
            {"status": "PAID"},
        )

        self.assertEqual(paid_response.status_code, 200)
        self.assertEqual(paid_response.data["count"], 1)

        self.assertEqual(
            paid_response.data["results"][0]["id"],
            self.paid_order1.id,
        )

        # Invalid filters must be rejected.
        invalid_response = self.client.get(
            url,
            {"status": "INVALID"},
        )

        self.assertEqual(
            invalid_response.status_code,
            400,
        )

    def test_order_history_isolated_between_coaches(self):

        self.client.force_authenticate(user=self.coach2)

        url = f"/api/students/{self.user1.id}/orders/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        self.assertEqual(
            response.data["results"][0]["amount_irr"],
            9000000,
        )

        # Coach 1 cannot access an unrelated student.
        self.client.force_authenticate(user=self.coach1)

        other_url = f"/api/students/{self.user2.id}/orders/"

        response = self.client.get(other_url)

        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_order_history(self):

        self.client.force_authenticate(user=self.user1)

        url = f"/api/students/{self.user1.id}/orders/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
