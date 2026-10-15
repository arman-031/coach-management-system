from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from orders.reconciliation import reconcile_payment_attempt
from rest_framework.test import APITestCase

from accounts.models import User
from students.models import StudentProfile
from programs.models import Program
from questionnaires.models import (
    QuestionnaireTemplate,
    TemplateQuestion,
    ProgramQuestionnaire,
)
from orders.gateways.base import (
    PaymentVerificationResult,
    GatewayStartRejected,
)
from orders.gateways.fake import FakeGateway
from orders.models import PaymentAttempt, PurchaseOrder
from orders.payment_services import (
    start_order_payment,
    verify_order_payment,
)
from orders.services import fulfill_verified_order

# ==========================================================
# 1. ORDER FULFILLMENT TESTS (4 tests)
# ==========================================================


class OrderFulfillmentTests(TestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000001",
            password="TestPassword123!",
            role=User.Role.COACH,
        )

        student_user = User.objects.create_user(
            phone="09120000002",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        self.student = StudentProfile.objects.create(
            user=student_user,
        )

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

        questionnaire.status = ProgramQuestionnaire.Status.SUBMITTED
        questionnaire.submitted_at = timezone.now()
        questionnaire.save(update_fields=["status", "submitted_at"])

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


# ==========================================================
# 2. PAYMENT FLOW TESTS (6 tests)
# ==========================================================



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

    # ==================================================
    # TEST 1: Successful payment and idempotency
    # ==================================================

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

    # ==================================================
    # TEST 2: Unverified payment
    # ==================================================

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

    # ==================================================
    # TEST 3: Wrong verified amount
    # ==================================================

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

    # ==================================================
    # TEST 4: Transaction rollback
    # ==================================================

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

    # ==================================================
    # TEST 5: Duplicate payment start
    # ==================================================

    def test_duplicate_payment_start_is_rejected(self):
        first_attempt = self.start_payment()

        with self.assertRaises(ValidationError):
            self.start_payment()

        self.assertEqual(
            PaymentAttempt.objects.filter(
                order=self.order,
            ).count(),
            1,
        )

        first_attempt.refresh_from_db()

        self.assertEqual(
            first_attempt.status,
            PaymentAttempt.Status.PENDING,
        )

    # ==================================================
    # TEST 6: Gateway explicitly rejects payment start
    # ==================================================

    def test_gateway_start_failure_allows_retry(self):
        with patch.object(
            self.gateway,
            "start_payment",
            side_effect=GatewayStartRejected(
                "درخواست توسط درگاه رد شد"
            ),
        ):
            with self.assertRaises(GatewayStartRejected):
                self.start_payment()

        failed_attempt = PaymentAttempt.objects.get(
            order=self.order,
        )

        self.assertEqual(
            failed_attempt.status,
            PaymentAttempt.Status.FAILED,
        )

        retry_attempt = self.start_payment()

        self.assertEqual(
            retry_attempt.status,
            PaymentAttempt.Status.PENDING,
        )

        self.assertEqual(
            PaymentAttempt.objects.filter(
                order=self.order,
            ).count(),
            2,
        )

    # ==================================================
    # TEST 7: Gateway timeout
    # ==================================================

    def test_gateway_timeout_blocks_duplicate_attempt(self):
        with patch.object(
            self.gateway,
            "start_payment",
            side_effect=TimeoutError(
                "ارتباط با درگاه قطع شد"
            ),
        ):
            with self.assertRaises(TimeoutError):
                self.start_payment()

        attempt = PaymentAttempt.objects.get(
            order=self.order,
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.CREATED,
        )

        with self.assertRaises(ValidationError):
            self.start_payment()

        self.assertEqual(
            PaymentAttempt.objects.filter(
                order=self.order,
            ).count(),
            1,
        )

    # ==================================================
    # TEST 8: Reconciliation - Manual review
    # ==================================================

    def test_reconcile_created_requires_manual_review(self):
        attempt = PaymentAttempt.objects.create(
            order=self.order,
            provider="FAKE",
            amount_irr=self.order.amount_irr,
            status=PaymentAttempt.Status.CREATED,
        )

        result = reconcile_payment_attempt(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.assertEqual(
            result,
            "MANUAL_REVIEW",
        )

        attempt.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.CREATED,
        )

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(self.order.program_id)

    # ==================================================
    # TEST 9: Reconciliation - Payment not confirmed
    # ==================================================

    def test_reconcile_unconfirmed_payment(self):
        attempt = self.start_payment()

        result = reconcile_payment_attempt(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.assertEqual(
            result,
            "NOT_CONFIRMED",
        )

        attempt.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PENDING,
        )

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(self.order.program_id)

    # ==================================================
    # TEST 10: Reconciliation - Verification timeout
    # ==================================================

    def test_reconcile_gateway_timeout(self):
        attempt = self.start_payment()

        with patch.object(
            self.gateway,
            "verify_payment",
            side_effect=TimeoutError("Gateway timeout"),
        ):
            result = reconcile_payment_attempt(
                attempt_id=attempt.id,
                gateway=self.gateway,
            )

        self.assertEqual(
            result,
            "RETRY_LATER",
        )

        attempt.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PENDING,
        )

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(self.order.program_id)

    # ==================================================
    # TEST 11: Reconciliation - Successful verification
    # ==================================================

    @patch("orders.services.initialize_program_questionnaire")
    def test_reconcile_successful_payment(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        self.gateway.simulate_success(
            attempt.gateway_authority
        )

        result = reconcile_payment_attempt(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.order.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(
            result,
            "VERIFIED",
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.VERIFIED,
        )

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PAID,
        )

        self.assertIsNotNone(self.order.program_id)

        self.assertTrue(
            Program.objects.filter(
                pk=self.order.program_id,
            ).exists()
        )



# ==========================================================
# 3. PAYMENT START API TESTS (5 tests)
# ==========================================================


class PaymentStartAPITests(APITestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000021",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.student_user = User.objects.create_user(
            phone="09120000022",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student, _ = StudentProfile.objects.get_or_create(
            user=self.student_user,
        )

        self.other_student = User.objects.create_user(
            phone="09120000023",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.order = PurchaseOrder.objects.create(
            student=self.student,
            coach=self.coach,
            program_type="BODYBUILDING",
            amount_irr=1500000,
            status=PurchaseOrder.Status.PENDING,
        )

        self.url = f"/api/orders/my/{self.order.id}/payments/start/"

    def test_owner_gets_gateway_unavailable(self):
        self.client.force_authenticate(user=self.student_user)

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            503,
        )

        self.assertFalse(
            PaymentAttempt.objects.filter(
                order=self.order,
            ).exists()
        )

    def test_other_student_cannot_start_payment(self):
        self.client.force_authenticate(user=self.other_student)

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_coach_cannot_start_payment(self):
        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_canceled_order_cannot_be_paid(self):
        self.order.status = PurchaseOrder.Status.CANCELED
        self.order.save(update_fields=["status", "updated_at"])

        self.client.force_authenticate(user=self.student_user)

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_student_cannot_override_amount(self):
        self.client.force_authenticate(user=self.student_user)

        response = self.client.post(
            self.url,
            {"amount_irr": 1},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    @override_settings(PAYMENT_CALLBACK_URL="https://example.invalid/callback/")
    @patch("orders.views.get_active_gateway")
    def test_gateway_timeout_returns_503(
        self,
        mock_get_gateway,
    ):
        gateway = FakeGateway()

        mock_get_gateway.return_value = (
            "FAKE",
            gateway,
        )

        self.client.force_authenticate(
            user=self.student_user,
        )

        with patch.object(
            gateway,
            "start_payment",
            side_effect=TimeoutError("Gateway timeout"),
        ):
            response = self.client.post(
                self.url,
                format="json",
            )

        self.assertEqual(
            response.status_code,
            503,
        )

        attempt = PaymentAttempt.objects.get(
            order=self.order,
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.CREATED,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )

        self.assertIsNone(
            self.order.program_id,
        )
        
        
    


# ==========================================================
# 4. STALE PAYMENT COMMAND TESTS (1 test)
# ==========================================================


class StalePaymentCommandTests(TestCase):

    def test_reports_old_created_attempt_without_changing_it(self):
        coach = User.objects.create_user(
            phone="09120000031",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        student_user = User.objects.create_user(
            phone="09120000032",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        student, _ = StudentProfile.objects.get_or_create(
            user=student_user,
        )

        order = PurchaseOrder.objects.create(
            student=student,
            coach=coach,
            program_type="BODYBUILDING",
            amount_irr=1500000,
        )

        attempt = PaymentAttempt.objects.create(
            order=order,
            provider="FAKE",
            amount_irr=order.amount_irr,
            status=PaymentAttempt.Status.CREATED,
        )

        old_time = timezone.now() - timedelta(
            minutes=20,
        )

        PaymentAttempt.objects.filter(pk=attempt.id).update(created_at=old_time)

        output = StringIO()

        call_command(
            "report_stale_payments",
            minutes=15,
            stdout=output,
        )

        self.assertIn(
            f"Attempt ID: {attempt.id}",
            output.getvalue(),
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.CREATED,
        )
