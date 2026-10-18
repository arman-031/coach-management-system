import re
from .base import PaymentVerificationResult
import requests

from .base import (
    GatewayStartRejected,
    PaymentGateway,
    PaymentStartResult,
)


class ZarinpalGateway(PaymentGateway):

    def __init__(self, *, merchant_id, sandbox=True):
        if not isinstance(merchant_id, str) or not re.fullmatch(
            r"[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}",
            merchant_id,
        ):
            raise ValueError("شناسه پذیرنده زرین‌پال معتبر نیست.")

        self.merchant_id = merchant_id
        self.sandbox = sandbox

        if sandbox:
            self.base_url = "https://sandbox.zarinpal.com"
        else:
            self.base_url = "https://payment.zarinpal.com"

    def start_payment(
        self,
        *,
        order_id,
        amount_irr,
        callback_url,
    ):
        if type(amount_irr) is not int or amount_irr <= 0:
            raise ValueError("مبلغ پرداخت معتبر نیست.")

        if not isinstance(callback_url, str) or not callback_url.startswith(
            ("https://", "http://")
        ):
            raise ValueError("آدرس بازگشت معتبر نیست.")

        url = f"{self.base_url}" "/pg/v4/payment/request.json"

        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_irr,
            "currency": "IRR",
            "description": f"خرید برنامه ورزشی - سفارش {order_id}",
            "callback_url": callback_url,
            "metadata": {
                "order_id": str(order_id),
            },
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=(5, 15),
                allow_redirects=False,
            )

        except requests.exceptions.Timeout as exc:
            raise TimeoutError("زمان ارتباط با زرین‌پال به پایان رسید.") from exc

        except requests.exceptions.RequestException as exc:
            raise ConnectionError("ارتباط با زرین‌پال برقرار نشد.") from exc

        if response.status_code >= 500:
            raise ConnectionError("پاسخ سرور زرین‌پال نامشخص است.")

        try:
            body = response.json()
        except ValueError as exc:
            raise ConnectionError("پاسخ زرین‌پال قابل پردازش نیست.") from exc

        if not isinstance(body, dict):
            raise ConnectionError("ساختار پاسخ زرین‌پال معتبر نیست.")

        data = body.get("data")

        if (
            200 <= response.status_code < 300
            and isinstance(data, dict)
            and data.get("code") == 100
        ):
            authority = data.get("authority")

            if not isinstance(authority, str) or not re.fullmatch(
                r"[A-Za-z0-9]{1,150}",
                authority,
            ):
                raise ConnectionError("شناسه پرداخت دریافتی معتبر نیست.")

            payment_url = f"{self.base_url}/pg/StartPay/{authority}"

            return PaymentStartResult(
                authority=authority,
                payment_url=payment_url,
            )

        errors = body.get("errors")

        if (
            200 <= response.status_code < 500
            and isinstance(errors, dict)
            and type(errors.get("code")) is int
        ):
            raise GatewayStartRejected("درخواست شروع پرداخت توسط زرین‌پال رد شد.")

        raise ConnectionError("نتیجه شروع پرداخت زرین‌پال نامشخص است.")

    def verify_payment(
        self,
        *,
        authority,
        expected_amount_irr,
    ):
        # Step 1: Validate inputs.
        if not isinstance(authority, str) or not re.fullmatch(
            r"[A-Za-z0-9]{1,150}",
            authority,
        ):
            raise ValueError("شناسه درخواست پرداخت معتبر نیست.")

        if type(expected_amount_irr) is not int or expected_amount_irr <= 0:
            raise ValueError("مبلغ پرداخت معتبر نیست.")

        # Step 2: Send verification request.
        url = f"{self.base_url}" "/pg/v4/payment/verify.json"

        payload = {
            "merchant_id": self.merchant_id,
            "amount": expected_amount_irr,
            "authority": authority,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=(5, 15),
                allow_redirects=False,
            )

        except requests.exceptions.Timeout as exc:
            raise TimeoutError("زمان استعلام پرداخت به پایان رسید.") from exc

        except requests.exceptions.RequestException as exc:
            raise ConnectionError("ارتباط با زرین‌پال برقرار نشد.") from exc

        # Step 3: Handle unknown server errors.
        if response.status_code >= 500:
            raise ConnectionError("پاسخ سرور زرین‌پال نامشخص است.")

        try:
            body = response.json()
        except ValueError as exc:
            raise ConnectionError("پاسخ زرین‌پال قابل پردازش نیست.") from exc

        if not isinstance(body, dict):
            raise ConnectionError("ساختار پاسخ زرین‌پال معتبر نیست.")

        data = body.get("data")
        errors = body.get("errors")

        # Handle an explicit gateway rejection.
        if (
            400 <= response.status_code < 500
            and isinstance(errors, dict)
            and type(errors.get("code")) is int
        ):
            return PaymentVerificationResult(
                verified=False,
            )

        if not 200 <= response.status_code < 300:
            raise ConnectionError("نتیجه استعلام زرین‌پال نامشخص است.")

        if not isinstance(data, dict) or type(data.get("code")) is not int:
            raise ConnectionError("پاسخ تأیید پرداخت معتبر نیست.")

        code = data["code"]

        # Step 4: Payment not confirmed.
        if code not in (100, 101):
            return PaymentVerificationResult(
                verified=False,
            )

        # Step 5: Validate transaction reference.
        ref_id = data.get("ref_id")

        if type(ref_id) is int:
            reference = str(ref_id) if ref_id > 0 else ""
        elif isinstance(ref_id, str):
            reference = ref_id
        else:
            reference = ""

        if not re.fullmatch(r"[0-9]{1,150}", reference) or int(reference) <= 0:
            raise ConnectionError("شناسه تراکنش تأییدشده معتبر نیست.")

        # Step 6: Return a trusted verification result.
        return PaymentVerificationResult(
            verified=True,
            reference=reference,
            amount_irr=expected_amount_irr,
        )
