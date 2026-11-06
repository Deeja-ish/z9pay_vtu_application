from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import Wallet, WalletLedger
from .serializers import WalletSerializer, WalletLedgerSerializer
from .paystack import PaystackClient
from .services import WalletService

User = get_user_model()


class WalletDetailView(generics.RetrieveAPIView):
    """GET /api/v1/wallet/ -> Returns current user's wallet balance and DVA bank details."""
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.wallet


class WalletLedgerListView(generics.ListAPIView):
    """GET /api/v1/wallet/ledger/ -> Returns the user's personal statement (credits/debits)."""
    serializer_class = WalletLedgerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WalletLedger.objects.filter(wallet=self.request.user.wallet)

class PaystackWebhookView(APIView):
    """
    Handles incoming webhooks from Paystack:
    1. dedicatedaccount.assign.success -> Saves the new bank account number to the user's Wallet.
    2. charge.success -> Credits the user's Wallet when they transfer money or pay via card.
    """
    permission_classes = [permissions.AllowAny] # Secured via HMAC signature instead of JWT

    def post(self, request, *args, **kwargs):
        signature = request.headers.get("x-paystack-signature", "")
        if not PaystackClient.verify_webhook_signature(request.body, signature):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        event = request.data.get("event")
        data = request.data.get("data", {})

        # CASE 1: Paystack finished assigning the user's Dedicated Virtual Account
        if event == "dedicatedaccount.assign.success":
            customer_email = data.get("customer", {}).get("email")
            customer_code = data.get("customer", {}).get("customer_code")
            dva = data.get("dedicated_account", {})

            if customer_email and dva:
                Wallet.objects.filter(user__email=customer_email).update(
                    paystack_customer_code=customer_code,
                    bank_name=dva.get("bank", {}).get("name"),
                    account_number=dva.get("account_number"),
                    account_name=dva.get("account_name"),
                )
            return Response({"status": "DVA updated"}, status=status.HTTP_200_OK)

        # CASE 2: A user funded their wallet (via Bank Transfer to DVA or Card Checkout)
        elif event == "charge.success":
            reference = data.get("reference")
            amount_in_kobo = data.get("amount", 0)
            customer_email = data.get("customer", {}).get("email")
            channel = data.get("channel") # "dedicated_nuban" for DVA transfer, "card" for ATM card

            # Convert kobo to Naira accurately using Decimal
            amount_in_naira = Decimal(str(amount_in_kobo)) / Decimal("100")

            user = User.objects.filter(email=customer_email).first()
            if user and amount_in_naira > Decimal("0.00"):
                source = (
                    WalletLedger.SourceType.PAYSTACK_DVA 
                    if channel == "dedicated_nuban" 
                    else WalletLedger.SourceType.PAYSTACK_CARD
                )
                WalletService.credit_wallet(
                    user_id=user.id,
                    amount=amount_in_naira,
                    reference=f"PSK-{reference}",
                    source=source,
                    description=f"Wallet funded via Paystack ({channel})",
                    metadata={"paystack_reference": reference, "channel": channel},
                )

            return Response({"status": "Wallet credited"}, status=status.HTTP_200_OK)

        # Return 200 OK for any other unhandled Paystack events so Paystack stops retrying
        return Response({"status": "Ignored"}, status=status.HTTP_200_OK)