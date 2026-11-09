from django.urls import path
from .views import NetworkListView, DataPlanListView

urlpatterns = [
    path("networks/", NetworkListView.as_view(), name="catalog-networks"),
    path("plans/", DataPlanListView.as_view(), name="catalog-plans"),
]