

def get_active_gateway():
    """
    Return (provider_name, gateway_instance)
    when a real payment gateway is configured.

    No real gateway is configured yet.
    FakeGateway must not be exposed publicly.
    """
    return None