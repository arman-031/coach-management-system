from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from students.models import StudentProfile
from programs.models import Program
from questionnaires.models import (
    QuestionnaireTemplate,
    TemplateQuestion,
    ProgramQuestionnaire,
)
from orders.gateways.base import PaymentVerificationResult
from orders.gateways.fake import FakeGateway
from orders.models import PaymentAttempt, PurchaseOrder
from orders.payment_services import (
    start_order_payment,
    verify_order_payment,
)
from .services import fulfill_verified_order


class OrderFulfillmentTests(TestCase):

    def setUp(self):
        # Create test coach.
        self.coach = User.objects.create_user(
            phone="09120000001",
            password="TestPassword123!",
            role=User.Role.COACH,
        )

        # Create test student.
        student_user = User.objects.create_user(
            phone="09120000002",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        self.student = StudentProfile.objects.create(
            user=student_user,
        )

        # Create bodybuilding questionnaire template.
        template = QuestionnaireTemplate.objects.create(
            program_type=Program.ProgramType.BODYBUILDING,
            title="پرسش‌نامه آزمایشی بدنسازی",
        )

        TemplateQuestion.objects.create(
            template=template,
            text="هدف اصلی شما چیست؟",
            answer_type=TemplateQuestion.AnswerType.SHORT_TEXT,
            is_required=True,
            order=1,
        )

    def create_order(self):
        return PurchaseOrder.objects.create(
            student=self.student,
            coach=self.coach,
            program_type=Program.ProgramType.BODYBUILDING,
            amount_irr=1500000,
        )

    def test_first_purchase(self):
        order = self.create_order()

        result = fulfill_verified_order(
            order_id=order.id,
            payment_reference="TEST-FIRST-001",
            verified_amount_irr=1500000,
        )

        program = result.program
        program.refresh_from_db()

        questionnaire = ProgramQuestionnaire.objects.get(
            program=program,
        )

        self.assertEqual(
            result.status,
            PurchaseOrder.Status.PAID,
        )

        self.assertEqual(
            program.status,
            Program.Status.WAITING,
        )

        self.assertEqual(
            questionnaire.status,
            ProgramQuestionnaire.Status.NOT_STARTED,
        )

        self.assertEqual(
            questionnaire.items.count(),
            1,
        )

        self.assertIsNone(program.published_at)

    def test_renewal(self):
        first_order = self.create_order()

        first_result = fulfill_verified_order(
            order_id=first_order.id,
            payment_reference="TEST-FIRST-002",
            verified_amount_irr=1500000,
        )

        questionnaire = ProgramQuestionnaire.objects.get(
            program=first_result.program,
        )

        # Simulate a previously submitted questionnaire.
        questionnaire.status = (
            ProgramQuestionnaire.Status.SUBMITTED
        )
        questionnaire.submitted_at = timezone.now()
        questionnaire.save(
            update_fields=["status", "submitted_at"]
        )

        renewal_order = self.create_order()

        renewal_result = fulfill_verified_order(
            order_id=renewal_order.id,
            payment_reference="TEST-RENEWAL-001",
            verified_amount_irr=1500000,
        )

        program = renewal_result.program
        program.refresh_from_db()

        self.assertEqual(
            program.status,
            Program.Status.PREPARING,
        )

        self.assertFalse(
            ProgramQuestionnaire.objects.filter(
                program=program,
            ).exists()
        )

    def test_duplicate_confirmation(self):
        order = self.create_order()

        first = fulfill_verified_order(
            order_id=order.id,
            payment_reference="TEST-DUPLICATE-001",
            verified_amount_irr=1500000,
        )

        second = fulfill_verified_order(
            order_id=order.id,
            payment_reference="TEST-DUPLICATE-001",
            verified_amount_irr=1500000,
        )

        self.assertEqual(
            first.program_id,
            second.program_id,
        )

        self.assertEqual(
            Program.objects.count(),
            1,
        )

    def test_wrong_payment_amount(self):
        order = self.create_order()

        with self.assertRaises(ValidationError):
            fulfill_verified_order(
                order_id=order.id,
                payment_reference="TEST-WRONG-001",
                verified_amount_irr=100,
            )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(order.program_id)

        self.assertEqual(
            Program.objects.count(),
            0,
        )


class PaymentFlowTests(TestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000011",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.student_user = User.objects.create_user(
            phone="09120000012",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student, _ = StudentProfile.objects.get_or_create(
            user=self.student_user,
        )

        self.order = PurchaseOrder.objects.create(
            student=self.student,
            coach=self.coach,
            program_type="BODYBUILDING",
            amount_irr=1500000,
            status=PurchaseOrder.Status.PENDING,
        )

        self.gateway = FakeGateway()

    def start_payment(self):
        attempt, result = start_order_payment(
            order_id=self.order.id,
            gateway=self.gateway,
            provider="FAKE",
            callback_url="http://localhost:8000/test/",
        )

        return attempt

    @patch("orders.services.initialize_program_questionnaire")
    def test_successful_payment_is_not_duplicated(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        self.gateway.simulate_success(
            attempt.gateway_authority
        )

        first_result = verify_order_payment(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PAID,
        )

        self.assertIsNotNone(self.order.program_id)

        self.assertEqual(
            first_result.status,
            PaymentAttempt.Status.VERIFIED,
        )

        program_id = self.order.program_id

        second_result = verify_order_payment(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.program_id,
            program_id,
        )

        self.assertEqual(
            first_result.id,
            second_result.id,
        )

        self.assertEqual(
            Program.objects.filter(
                student=self.student,
                program_type="BODYBUILDING",
            ).count(),
            1,
        )

    def test_unverified_payment_does_not_create_program(self):
        attempt = self.start_payment()

        with self.assertRaises(ValidationError):
            verify_order_payment(
                attempt_id=attempt.id,
                gateway=self.gateway,
            )

        self.order.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(self.order.program_id)

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PENDING,
        )

    def test_wrong_verified_amount_is_rejected(self):
        attempt = self.start_payment()

        fake_result = PaymentVerificationResult(
            verified=True,
            reference="FAKE-WRONG-AMOUNT",
            amount_irr=self.order.amount_irr - 1,
        )

        with patch.object(
            self.gateway,
            "verify_payment",
            return_value=fake_result,
        ):
            with self.assertRaises(ValidationError):
                verify_order_payment(
                    attempt_id=attempt.id,
                    gateway=self.gateway,
                )

        self.order.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(self.order.program_id)

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PENDING,
        )

    @patch(
        "orders.services.initialize_program_questionnaire",
        side_effect=ValidationError(
            "خطای آزمایشی هنگام ساخت پرسش‌نامه"
        ),
    )
    def test_fulfillment_failure_rolls_back(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        self.gateway.simulate_success(
            attempt.gateway_authority
        )

        with self.assertRaises(ValidationError):
            verify_order_payment(
                attempt_id=attempt.id,
                gateway=self.gateway,
            )

        self.order.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(self.order.program_id)

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PENDING,
        )

        self.assertFalse(
            Program.objects.filter(
                student=self.student,
                program_type="BODYBUILDING",
            ).exists()
        )