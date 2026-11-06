from django.urls import path
from .views import WalletDetailView, WalletLedgerListView, PaystackWebhookView

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("ledger/", WalletLedgerListView.as_view(), name="wallet-ledger"),
    path("webhook/", PaystackWebhookView.as_view(), name="paystack-webhook"),
]