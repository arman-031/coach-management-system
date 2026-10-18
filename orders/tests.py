from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from orders.gateways.registry import get_active_gateway
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from requests.exceptions import Timeout as RequestsTimeout
from orders.gateways.zarinpal import ZarinpalGateway
from rest_framework.test import APITestCase
from orders.pricing import PROGRAM_PRICES_IRR
from accounts.models import User
from students.models import StudentProfile
from programs.models import Program
from questionnaires.models import (
    QuestionnaireTemplate,
    TemplateQuestion,
    ProgramQuestionnaire,
)
from django.test import SimpleTestCase

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
from orders.reconciliation import reconcile_payment_attempt
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
        self.assertEqual(questionnaire.items.count(), 1)
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
        self.assertEqual(Program.objects.count(), 1)

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
        self.assertEqual(Program.objects.count(), 0)


# ==========================================================
# 2. PAYMENT FLOW AND RECONCILIATION TESTS (13 tests)
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

    # TEST 1: Successful payment and idempotency

    @patch("orders.services.initialize_program_questionnaire")
    def test_successful_payment_is_not_duplicated(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        self.gateway.simulate_success(attempt.gateway_authority)

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

        self.assertEqual(self.order.program_id, program_id)
        self.assertEqual(first_result.id, second_result.id)

        self.assertEqual(
            Program.objects.filter(
                student=self.student,
                program_type="BODYBUILDING",
            ).count(),
            1,
        )

    # TEST 2: Unverified payment

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

    # TEST 3: Wrong verified amount

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

    # TEST 4: Transaction rollback

    @patch(
        "orders.services.initialize_program_questionnaire",
        side_effect=ValidationError("خطای آزمایشی هنگام ساخت پرسش‌نامه"),
    )
    def test_fulfillment_failure_rolls_back(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        self.gateway.simulate_success(attempt.gateway_authority)

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

    # TEST 5: Duplicate payment start

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

    # TEST 6: Gateway rejected payment start

    def test_gateway_start_failure_allows_retry(self):
        with patch.object(
            self.gateway,
            "start_payment",
            side_effect=GatewayStartRejected("درخواست توسط درگاه رد شد"),
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

    # TEST 7: Gateway timeout

    def test_gateway_timeout_blocks_duplicate_attempt(self):
        with patch.object(
            self.gateway,
            "start_payment",
            side_effect=TimeoutError("ارتباط با درگاه قطع شد"),
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

    # TEST 8: Created payment requires manual review

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

        self.assertEqual(result, "MANUAL_REVIEW")

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

    # TEST 9: Payment not confirmed

    def test_reconcile_unconfirmed_payment(self):
        attempt = self.start_payment()

        result = reconcile_payment_attempt(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.assertEqual(result, "NOT_CONFIRMED")

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

    # TEST 10: Verification timeout

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

        self.assertEqual(result, "RETRY_LATER")

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

    # TEST 11: Successful payment reconciliation

    @patch("orders.services.initialize_program_questionnaire")
    def test_reconcile_successful_payment(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        self.gateway.simulate_success(attempt.gateway_authority)

        result = reconcile_payment_attempt(
            attempt_id=attempt.id,
            gateway=self.gateway,
        )

        self.order.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(result, "VERIFIED")
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

    # TEST 12: Command preview must not change payment

    def test_reconcile_command_preview_does_not_change_payment(self):
        attempt = self.start_payment()

        old_time = timezone.now() - timedelta(minutes=20)

        PaymentAttempt.objects.filter(
            pk=attempt.id,
        ).update(
            created_at=old_time,
        )

        self.gateway.simulate_success(attempt.gateway_authority)

        output = StringIO()

        with patch(
            "orders.management.commands."
            "reconcile_pending_payments.get_active_gateway"
        ) as mock_gateway:

            call_command(
                "reconcile_pending_payments",
                minutes=15,
                stdout=output,
            )

            mock_gateway.assert_not_called()

        attempt.refresh_from_db()
        self.order.refresh_from_db()

        self.assertIn(
            f"Attempt ID: {attempt.id}",
            output.getvalue(),
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PENDING,
        )
        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )
        self.assertIsNone(self.order.program_id)

    # TEST 13: Command execution verifies payment

    @patch("orders.services.initialize_program_questionnaire")
    def test_reconcile_command_execute_verifies_payment(
        self,
        mock_initialize,
    ):
        attempt = self.start_payment()

        old_time = timezone.now() - timedelta(minutes=20)

        PaymentAttempt.objects.filter(
            pk=attempt.id,
        ).update(
            created_at=old_time,
        )

        self.gateway.simulate_success(attempt.gateway_authority)

        with patch(
            "orders.management.commands."
            "reconcile_pending_payments.get_active_gateway",
            return_value=("FAKE", self.gateway),
        ):
            call_command(
                "reconcile_pending_payments",
                minutes=15,
                execute=True,
                stdout=StringIO(),
            )

        attempt.refresh_from_db()
        self.order.refresh_from_db()

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

    def test_stale_report_includes_canceled_order(self):

        # Cancel the order.
        self.order.status = PurchaseOrder.Status.CANCELED
        self.order.save(update_fields=["status", "updated_at"])

        # Create an unresolved payment attempt.
        attempt = PaymentAttempt.objects.create(
            order=self.order,
            provider="FAKE",
            amount_irr=self.order.amount_irr,
            status=PaymentAttempt.Status.CREATED,
        )

        # Make the attempt 20 minutes old.
        old_time = timezone.now() - timedelta(minutes=20)

        PaymentAttempt.objects.filter(pk=attempt.id).update(created_at=old_time)

        output = StringIO()

        # Execute the read-only management command.
        call_command(
            "report_stale_payments",
            minutes=15,
            stdout=output,
        )

        report = output.getvalue()

        # The canceled order must appear.
        self.assertIn(
            f"Attempt ID: {attempt.id}",
            report,
        )

        self.assertIn(
            "Order Status: CANCELED",
            report,
        )

        self.assertIn(
            "Has Authority: NO",
            report,
        )

        # No payment or order status must change.
        attempt.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.CREATED,
        )

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.CANCELED,
        )

        self.assertIsNone(
            self.order.program_id,
        )


# ==========================================================
# 3. PAYMENT START API TESTS (6 tests)
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

        self.assertEqual(response.status_code, 503)

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

        self.assertEqual(response.status_code, 404)

    def test_coach_cannot_start_payment(self):
        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_canceled_order_cannot_be_paid(self):
        self.order.status = PurchaseOrder.Status.CANCELED
        self.order.save(update_fields=["status", "updated_at"])

        self.client.force_authenticate(user=self.student_user)

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_student_cannot_override_amount(self):
        self.client.force_authenticate(user=self.student_user)

        response = self.client.post(
            self.url,
            {"amount_irr": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

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

        self.assertEqual(response.status_code, 503)

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
        self.assertIsNone(self.order.program_id)


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

        old_time = timezone.now() - timedelta(minutes=20)

        PaymentAttempt.objects.filter(
            pk=attempt.id,
        ).update(
            created_at=old_time,
        )

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


class ZarinpalGatewayTests(TestCase):

    def setUp(self):
        self.gateway = ZarinpalGateway(
            merchant_id="12345678-1234-1234-1234-123456789012",
            sandbox=True,
        )

    @patch("orders.gateways.zarinpal.requests.post")
    def test_start_payment_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "code": 100,
                "authority": "S123456789",
            },
            "errors": [],
        }

        result = self.gateway.start_payment(
            order_id=10,
            amount_irr=1500000,
            callback_url="https://example.com/callback/",
        )

        self.assertEqual(
            result.authority,
            "S123456789",
        )

        self.assertEqual(
            result.payment_url,
            "https://sandbox.zarinpal.com/pg/StartPay/S123456789",
        )

        payload = mock_post.call_args.kwargs["json"]

        self.assertEqual(payload["amount"], 1500000)
        self.assertEqual(payload["currency"], "IRR")
        self.assertEqual(payload["metadata"]["order_id"], "10")

    @patch("orders.gateways.zarinpal.requests.post")
    def test_gateway_timeout(self, mock_post):
        mock_post.side_effect = RequestsTimeout("Connection timed out")

        with self.assertRaises(TimeoutError):
            self.gateway.start_payment(
                order_id=10,
                amount_irr=1500000,
                callback_url="https://example.com/callback/",
            )

    @patch("orders.gateways.zarinpal.requests.post")
    def test_explicit_gateway_rejection(self, mock_post):
        mock_post.return_value.status_code = 422
        mock_post.return_value.json.return_value = {
            "data": [],
            "errors": {
                "code": -9,
                "message": "Invalid merchant",
            },
        }

        with self.assertRaises(GatewayStartRejected):
            self.gateway.start_payment(
                order_id=10,
                amount_irr=1500000,
                callback_url="https://example.com/callback/",
            )


class ZarinpalVerifyTests(SimpleTestCase):

    def setUp(self):
        self.gateway = ZarinpalGateway(
            merchant_id="12345678-1234-1234-1234-123456789012",
            sandbox=True,
        )

    @patch("orders.gateways.zarinpal.requests.post")
    def test_verify_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "code": 100,
                "ref_id": 123456789,
            },
            "errors": [],
        }

        result = self.gateway.verify_payment(
            authority="S123456789",
            expected_amount_irr=1500000,
        )

        self.assertTrue(result.verified)
        self.assertEqual(result.reference, "123456789")
        self.assertEqual(result.amount_irr, 1500000)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 1500000)
        self.assertEqual(payload["authority"], "S123456789")

    @patch("orders.gateways.zarinpal.requests.post")
    def test_already_verified(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "code": 101,
                "ref_id": 123456789,
            },
            "errors": [],
        }

        result = self.gateway.verify_payment(
            authority="S123456789",
            expected_amount_irr=1500000,
        )

        self.assertTrue(result.verified)
        self.assertEqual(result.reference, "123456789")

    @patch("orders.gateways.zarinpal.requests.post")
    def test_unconfirmed_payment(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "code": -22,
            },
            "errors": [],
        }

        result = self.gateway.verify_payment(
            authority="S123456789",
            expected_amount_irr=1500000,
        )

        self.assertFalse(result.verified)

    @patch("orders.gateways.zarinpal.requests.post")
    def test_verify_timeout(self, mock_post):
        mock_post.side_effect = RequestsTimeout()

        with self.assertRaises(TimeoutError):
            self.gateway.verify_payment(
                authority="S123456789",
                expected_amount_irr=1500000,
            )

    @patch("orders.gateways.zarinpal.requests.post")
    def test_success_without_reference_is_rejected(
        self,
        mock_post,
    ):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "code": 100,
            },
            "errors": [],
        }

        with self.assertRaises(ConnectionError):
            self.gateway.verify_payment(
                authority="S123456789",
                expected_amount_irr=1500000,
            )


class ZarinpalCallbackTests(APITestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000071",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        student_user = User.objects.create_user(
            phone="09120000072",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student, _ = StudentProfile.objects.get_or_create(
            user=student_user,
        )

        self.order = PurchaseOrder.objects.create(
            student=self.student,
            coach=self.coach,
            program_type="BODYBUILDING",
            amount_irr=1500000,
            status=PurchaseOrder.Status.PENDING,
        )

        self.gateway = FakeGateway()

        self.attempt, _ = start_order_payment(
            order_id=self.order.id,
            gateway=self.gateway,
            provider="ZARINPAL",
            callback_url="https://example.invalid/callback/",
        )

        self.url = "/api/orders/payments/zarinpal/callback/"

        gateway_patch = patch(
            "orders.views.get_active_gateway",
            return_value=("ZARINPAL", self.gateway),
        )
        gateway_patch.start()
        self.addCleanup(gateway_patch.stop)

    def callback(self, payment_status="OK", authority=None):
        return self.client.get(
            self.url,
            {
                "Authority": (
                    self.attempt.gateway_authority if authority is None else authority
                ),
                "Status": payment_status,
            },
        )

    # Test 1: A genuine payment creates one program.
    @patch("orders.services.initialize_program_questionnaire")
    def test_successful_callback(self, mock_initialize):
        self.gateway.simulate_success(self.attempt.gateway_authority)

        response = self.callback()

        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PAID,
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.VERIFIED,
        )
        self.assertIsNotNone(self.order.program_id)

    # Test 2: Forging Status=OK must not complete payment.
    def test_fake_success_callback_is_not_accepted(self):
        response = self.callback(payment_status="OK")

        self.assertEqual(response.status_code, 202)

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )
        self.assertIsNone(self.order.program_id)

    # Test 3: NOK must not mark the attempt as failed.
    def test_nok_callback_keeps_payment_pending(self):
        response = self.callback(payment_status="NOK")

        self.assertEqual(response.status_code, 202)

        self.attempt.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.PENDING,
        )
        self.assertEqual(
            self.order.status,
            PurchaseOrder.Status.PENDING,
        )
        self.assertIsNone(self.order.program_id)

    # Test 4: Unknown authority must be rejected.
    def test_unknown_authority_returns_404(self):
        response = self.callback(authority="UNKNOWN123456789")

        self.assertEqual(response.status_code, 404)

        self.order.refresh_from_db()
        self.assertIsNone(self.order.program_id)

    # Test 5: Repeated callbacks must not create duplicates.
    @patch("orders.services.initialize_program_questionnaire")
    def test_repeated_callback_is_idempotent(
        self,
        mock_initialize,
    ):
        self.gateway.simulate_success(self.attempt.gateway_authority)

        first = self.callback()
        second = self.callback()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        self.assertEqual(
            Program.objects.filter(
                student=self.student,
                program_type="BODYBUILDING",
            ).count(),
            1,
        )


@override_settings(
    ZARINPAL_ENABLED=True,
    ZARINPAL_SANDBOX=True,
    ZARINPAL_MERCHANT_ID=("12345678-1234-1234-1234-123456789012"),
    PAYMENT_CALLBACK_URL=(
        "https://example.com" "/api/orders/payments/zarinpal/callback/"
    ),
)
class ZarinpalRegistryTests(SimpleTestCase):

    def test_sandbox_gateway_is_available(self):
        active_gateway = get_active_gateway()

        self.assertIsNotNone(active_gateway)

        provider, gateway = active_gateway

        self.assertEqual(provider, "ZARINPAL")
        self.assertIsInstance(
            gateway,
            ZarinpalGateway,
        )
        self.assertTrue(gateway.sandbox)

    @override_settings(ZARINPAL_ENABLED=False)
    def test_disabled_gateway_returns_none(self):
        self.assertIsNone(get_active_gateway())

    @override_settings(ZARINPAL_SANDBOX=False)
    def test_production_gateway_is_blocked(self):
        self.assertIsNone(get_active_gateway())

    @override_settings(ZARINPAL_MERCHANT_ID="INVALID")
    def test_invalid_merchant_is_rejected(self):
        self.assertIsNone(get_active_gateway())

    @override_settings(
        PAYMENT_CALLBACK_URL=(
            "http://example.com" "/api/orders/payments/zarinpal/callback/"
        )
    )
    def test_insecure_callback_is_rejected(self):
        self.assertIsNone(get_active_gateway())


@override_settings(
    PAYMENT_CALLBACK_URL=(
        "https://example.com" "/api/orders/payments/zarinpal/callback/"
    )
)
class CompletePurchaseFlowTests(APITestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000081",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        self.student_user = User.objects.create_user(
            phone="09120000082",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student, _ = StudentProfile.objects.get_or_create(
            user=self.student_user,
        )

        # Create questionnaire templates
        # for all three program types.
        for program_type in [
            Program.ProgramType.BODYBUILDING,
            Program.ProgramType.NUTRITION,
            Program.ProgramType.CORRECTIVE,
        ]:
            template = QuestionnaireTemplate.objects.create(
                program_type=program_type,
                title=f"پرسش‌نامه {program_type}",
            )

            TemplateQuestion.objects.create(
                template=template,
                text="هدف شما از دریافت برنامه چیست؟",
                answer_type=TemplateQuestion.AnswerType.SHORT_TEXT,
                order=1,
            )

        self.gateway = FakeGateway()

        self.client.force_authenticate(user=self.student_user)

    def test_complete_purchase_for_all_program_types(self):

        program_types = [
            Program.ProgramType.BODYBUILDING,
            Program.ProgramType.NUTRITION,
            Program.ProgramType.CORRECTIVE,
        ]

        # FakeGateway is used ONLY in this test.
        # Production payment remains disabled.
        with patch(
            "orders.views.get_active_gateway",
            return_value=("ZARINPAL", self.gateway),
        ):

            for program_type in program_types:

                with self.subTest(program_type=program_type):

                    # Step 1: Student creates an order.
                    create_response = self.client.post(
                        "/api/orders/create/",
                        {"program_type": program_type},
                        format="json",
                    )

                    self.assertEqual(
                        create_response.status_code,
                        201,
                    )

                    order_id = create_response.data["id"]

                    order = PurchaseOrder.objects.get(pk=order_id)

                    self.assertEqual(
                        order.amount_irr,
                        PROGRAM_PRICES_IRR[program_type],
                    )

                    self.assertEqual(
                        order.status,
                        PurchaseOrder.Status.PENDING,
                    )

                    self.assertIsNone(order.program_id)

                    # Step 2: Start the payment.
                    start_response = self.client.post(
                        f"/api/orders/my/{order_id}/payments/start/",
                        format="json",
                    )

                    self.assertEqual(
                        start_response.status_code,
                        201,
                    )

                    attempt = PaymentAttempt.objects.get(
                        pk=start_response.data["attempt_id"]
                    )

                    self.assertEqual(
                        attempt.status,
                        PaymentAttempt.Status.PENDING,
                    )

                    # No program before verification.
                    order.refresh_from_db()
                    self.assertIsNone(order.program_id)

                    # Step 3: Simulate a successful payment.
                    self.gateway.simulate_success(attempt.gateway_authority)

                    # Step 4: Call the payment callback.
                    callback_url = "/api/orders/payments/" "zarinpal/callback/"

                    callback_data = {
                        "Authority": attempt.gateway_authority,
                        "Status": "OK",
                    }

                    callback_response = self.client.get(
                        callback_url,
                        callback_data,
                    )

                    self.assertEqual(
                        callback_response.status_code,
                        200,
                    )

                    # Step 5: Check database changes.
                    order.refresh_from_db()
                    attempt.refresh_from_db()

                    self.assertEqual(
                        order.status,
                        PurchaseOrder.Status.PAID,
                    )

                    self.assertEqual(
                        attempt.status,
                        PaymentAttempt.Status.VERIFIED,
                    )

                    self.assertIsNotNone(order.program_id)

                    program = Program.objects.get(pk=order.program_id)

                    self.assertEqual(
                        program.program_type,
                        program_type,
                    )

                    self.assertEqual(
                        program.student,
                        self.student,
                    )

                    self.assertEqual(
                        program.duration_days,
                        45,
                    )

                    self.assertEqual(
                        program.status,
                        Program.Status.WAITING,
                    )

                    # Countdown starts at publication.
                    self.assertIsNone(program.published_at)

                    # Initial questionnaire must exist.
                    questionnaire = ProgramQuestionnaire.objects.get(program=program)

                    self.assertEqual(
                        questionnaire.status,
                        ProgramQuestionnaire.Status.NOT_STARTED,
                    )

                    self.assertEqual(
                        questionnaire.items.count(),
                        1,
                    )

                    # Step 6: Repeated callback must be safe.
                    repeated_response = self.client.get(
                        callback_url,
                        callback_data,
                    )

                    self.assertEqual(
                        repeated_response.status_code,
                        200,
                    )

                    self.assertEqual(
                        Program.objects.filter(
                            purchase_order=order,
                        ).count(),
                        1,
                    )

        # Three separate purchases = three programs.
        self.assertEqual(
            Program.objects.filter(
                student=self.student,
            ).count(),
            3,
        )


class StudentOrderSummaryTests(APITestCase):

    def test_student_sees_purchased_program_status(self):
        coach = User.objects.create_user(
            phone="09120000091",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        student_user = User.objects.create_user(
            phone="09120000092",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        student, _ = StudentProfile.objects.get_or_create(
            user=student_user,
        )

        program = Program.objects.create(
            student=student,
            program_type=Program.ProgramType.BODYBUILDING,
            created_by=coach,
            status=Program.Status.WAITING,
        )

        order = PurchaseOrder.objects.create(
            student=student,
            coach=coach,
            program_type=Program.ProgramType.BODYBUILDING,
            amount_irr=1500000,
            status=PurchaseOrder.Status.PAID,
            program=program,
            payment_reference="TEST-STUDENT-SUMMARY-001",
        )

        self.client.force_authenticate(user=student_user)

        response = self.client.get("/api/orders/my/")

        self.assertEqual(response.status_code, 200)

        orders = response.data["results"]

        self.assertEqual(len(orders), 1)

        result = orders[0]

        self.assertEqual(result["id"], order.id)
        self.assertEqual(result["status"], "PAID")
        self.assertEqual(result["program"], program.id)

        self.assertEqual(
            result["program_status"],
            "WAITING",
        )

        self.assertEqual(
            result["program_status_display"],
            "در انتظار",
        )


class StudentDataIsolationTests(APITestCase):

    def setUp(self):
        # Create coach
        self.coach = User.objects.create_user(
            phone="09120000101",
            password="TestPass123!",
            role=User.Role.COACH,
        )

        # Create first student
        self.user1 = User.objects.create_user(
            phone="09120000102",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student1, _ = StudentProfile.objects.get_or_create(
            user=self.user1,
        )

        # Create second student
        self.user2 = User.objects.create_user(
            phone="09120000103",
            password="TestPass123!",
            role=User.Role.STUDENT,
        )

        self.student2, _ = StudentProfile.objects.get_or_create(
            user=self.user2,
        )

        # First student's order
        self.order1 = PurchaseOrder.objects.create(
            student=self.student1,
            coach=self.coach,
            program_type=Program.ProgramType.BODYBUILDING,
            amount_irr=1500000,
            status=PurchaseOrder.Status.PENDING,
        )

        # Second student's order
        self.order2 = PurchaseOrder.objects.create(
            student=self.student2,
            coach=self.coach,
            program_type=Program.ProgramType.NUTRITION,
            amount_irr=1200000,
            status=PurchaseOrder.Status.PENDING,
        )

        # Second student's payment attempt
        self.payment2 = PaymentAttempt.objects.create(
            order=self.order2,
            provider="FAKE",
            amount_irr=self.order2.amount_irr,
            status=PaymentAttempt.Status.CREATED,
        )

        # Second student's active program
        self.program2 = Program.objects.create(
            student=self.student2,
            created_by=self.coach,
            program_type=Program.ProgramType.NUTRITION,
            status=Program.Status.ACTIVE,
        )

        # Authenticate as first student
        self.client.force_authenticate(user=self.user1)

    # ==========================================
    # TEST 1: Student sees only own orders
    # ==========================================

    def test_student_sees_only_own_orders(self):

        response = self.client.get("/api/orders/my/")

        self.assertEqual(response.status_code, 200)

        orders = response.data["results"]

        order_ids = [order["id"] for order in orders]

        self.assertIn(
            self.order1.id,
            order_ids,
        )

        self.assertNotIn(
            self.order2.id,
            order_ids,
        )

    # ==========================================
    # TEST 2: Cannot access another payment history
    # ==========================================

    def test_student_cannot_access_other_payments(self):

        response = self.client.get(f"/api/orders/my/{self.order2.id}/payments/")

        self.assertEqual(
            response.status_code,
            404,
        )

    # ==========================================
    # TEST 3: Cannot access another student's program
    # ==========================================

    def test_student_cannot_access_other_program(self):

        response = self.client.get(f"/api/programs/my/{self.program2.id}/")

        self.assertEqual(
            response.status_code,
            404,
        )
