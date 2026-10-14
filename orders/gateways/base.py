

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentStartResult:
    authority: str
    payment_url: str


@dataclass(frozen=True)
class PaymentVerificationResult:
    verified: bool
    reference: str | None = None
    amount_irr: int | None = None


class PaymentGateway(ABC):

    @abstractmethod
    def start_payment(
        self,
        *,
        order_id: int,
        amount_irr: int,
        callback_url: str,
    ) -> PaymentStartResult:
        pass

    @abstractmethod
    def verify_payment(
        self,
        *,
        authority: str,
        expected_amount_irr: int,
    ) -> PaymentVerificationResult:
        pass