

from django.utils import timezone

from .models import Program


def expire_due_programs():
    now = timezone.now()

    return Program.objects.filter(
        status=Program.Status.ACTIVE,
        expires_at__isnull=False,
        expires_at__lte=now,
    ).update(
        status=Program.Status.EXPIRED,
    )