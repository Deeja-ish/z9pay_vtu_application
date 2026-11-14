from django.urls import path
from .views import TransactionListView, TransactionDetailView

urlpatterns = [
    path("", TransactionListView.as_view(), name="transaction-list"),
    path("<str:reference>/", TransactionDetailView.as_view(), name="transaction-detail"),
]