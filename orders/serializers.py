
from rest_framework import serializers

from programs.models import Program
from .models import PurchaseOrder


class PurchaseOrderCreateSerializer(serializers.Serializer):

    program_type = serializers.ChoiceField(
        choices=Program.ProgramType.choices,
    )

    def to_internal_value(self, data):

        if isinstance(data, dict):
            unexpected = set(data) - {"program_type"}

            if unexpected:
                raise serializers.ValidationError({
                    field: "ارسال این فیلد مجاز نیست."
                    for field in unexpected
                })

        return super().to_internal_value(data)


class PurchaseOrderReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = PurchaseOrder

        fields = (
            "id",
            "program_type",
            "amount_irr",
            "status",
            "program",
            "created_at",
        )

        read_only_fields = fields