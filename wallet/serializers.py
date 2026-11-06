from rest_framework import serializers
from .models import Wallet, WalletLedger


class WalletSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "phone_number",
            "balance",
            "bank_name",
            "account_number",
            "account_name",
            "is_locked",
            "updated_at",
        ]


class WalletLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletLedger
        fields = [
            "id",
            "reference",
            "transaction_type",
            "source",
            "amount",
            "balance_before",
            "balance_after",
            "description",
            "created_at",
        ]