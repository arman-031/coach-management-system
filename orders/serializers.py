from rest_framework import serializers

from programs.models import Program
from .models import PurchaseOrder, PaymentAttempt

# ==========================================
# 1. Create Purchase Order
# ==========================================


class PurchaseOrderCreateSerializer(serializers.Serializer):

    program_type = serializers.ChoiceField(
        choices=Program.ProgramType.choices,
    )

    def to_internal_value(self, data):

        if isinstance(data, dict):
            unexpected = set(data) - {"program_type"}

            if unexpected:
                raise serializers.ValidationError(
                    {field: "ارسال این فیلد مجاز نیست." for field in unexpected}
                )

        return super().to_internal_value(data)


# ==========================================
# 2. Read Purchase Order
# ==========================================


class PurchaseOrderReadSerializer(serializers.ModelSerializer):

    program_status = serializers.CharField(
        source="program.status",
        read_only=True,
        allow_null=True,
    )

    program_status_display = serializers.CharField(
        source="program.get_status_display",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PurchaseOrder

        fields = (
            "id",
            "program_type",
            "amount_irr",
            "status",
            "program",
            "program_status",
            "program_status_display",
            "created_at",
        )

        read_only_fields = fields


# ==========================================
# 3. Read Payment Attempts
# ==========================================


class PaymentAttemptReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentAttempt

        fields = (
            "id",
            "tracking_id",
            "provider",
            "amount_irr",
            "status",
            "created_at",
            "verified_at",
        )

        read_only_fields = fields
