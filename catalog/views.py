from rest_framework import generics, permissions
from .models import Network, DataPlan
from .serializers import NetworkSerializer, DataPlanSerializer


class NetworkListView(generics.ListAPIView):
    """
    GET /api/v1/catalog/networks/
    Lists active networks (MTN, Airtel, Glo, 9mobile).
    """
    serializer_class = NetworkSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Network.objects.filter(is_active=True)


class DataPlanListView(generics.ListAPIView):
    """
    GET /api/v1/catalog/plans/?network=MTN&category=SME
    Lists available data plans for active networks.
    """
    serializer_class = DataPlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = DataPlan.objects.select_related("network").filter(
            is_active=True,
            network__is_active=True,  # Circuit breaker: hide plans if the parent network is turned off!
        )
        
        network_code = self.request.query_params.get("network")
        category = self.request.query_params.get("category")

        if network_code:
            queryset = queryset.filter(network__code__iexact=network_code)
        if category:
            queryset = queryset.filter(category__iexact=category)

        return queryset