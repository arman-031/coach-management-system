from urllib.parse import urlsplit

from django.conf import settings

from .zarinpal import ZarinpalGateway

CALLBACK_PATH = "/api/orders/payments/zarinpal/callback/"


def get_active_gateway():
    """
    Return the configured payment gateway.

    For now, only Zarinpal Sandbox is allowed.
    Production remains disabled.
    """

    # Step 1: Check whether payments are enabled.
    if getattr(settings, "ZARINPAL_ENABLED", False) is not True:
        return None

    # Step 2: Block real payments for now.
    if getattr(settings, "ZARINPAL_SANDBOX", True) is not True:
        return None

    merchant_id = getattr(
        settings,
        "ZARINPAL_MERCHANT_ID",
        "",
    )

    callback_url = getattr(
        settings,
        "PAYMENT_CALLBACK_URL",
        "",
    )

    # Step 3: Check required settings.
    if not isinstance(merchant_id, str) or not isinstance(callback_url, str):
        return None

    try:
        parsed_url = urlsplit(callback_url)
    except ValueError:
        return None

    # Require an HTTPS callback with the correct path.
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.path != CALLBACK_PATH
        or parsed_url.query
        or parsed_url.fragment
        or parsed_url.username
        or parsed_url.password
    ):
        return None

    # Step 4: Create the trusted gateway.
    try:
        gateway = ZarinpalGateway(
            merchant_id=merchant_id.strip(),
            sandbox=True,
        )
    except ValueError:
        return None

    return "ZARINPAL", gateway
