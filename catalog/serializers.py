from rest_framework import serializers
from .models import Network, DataPlan


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = ["id", "name", "code"]


class DataPlanSerializer(serializers.ModelSerializer):
    network_code = serializers.CharField(source="network.code", read_only=True)
    network_name = serializers.CharField(source="network.name", read_only=True)
    price = serializers.DecimalField(source="selling_price", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DataPlan
        fields = [
            "id",
            "network_code",
            "network_name",
            "name",
            "category",
            "validity",
            "price",
        ]