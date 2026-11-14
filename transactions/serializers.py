from rest_framework import serializers
from catalog.models import DataPlan
from .models import DataTransaction


class DataPurchaseInputSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=15, min_length=10)
    reference = serializers.CharField(max_length=100)

    def validate_plan_id(self, value):
        try:
            plan = DataPlan.objects.select_related("network").get(
                id=value, 
                is_active=True, 
                network__is_active=True
            )
            return plan
        except DataPlan.DoesNotExist:
            raise serializers.ValidationError("Selected data plan does not exist or is currently unavailable.")


class DataTransactionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    network = serializers.CharField(source="plan.network.code", read_only=True)

    class Meta:
        model = DataTransaction
        fields = [
            "id",
            "reference",
            "z9pay_reference",
            "network",
            "plan_name",
            "phone_number",
            "amount_charged",
            "status",
            "response_message",
            "created_at",
            "updated_at",
        ]