from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Wallet, WalletLedger


class InsufficientBalanceError(Exception):
    pass


class DuplicateTransactionError(Exception):
    pass


class WalletService:
    @staticmethod
    @transaction.atomic
    def credit_wallet(
        user_id, 
        amount: Decimal, 
        reference: str, 
        source: str, 
        description: str, 
        metadata: dict = None
    ) -> WalletLedger:
        """
        Safely credits a user's wallet using row-level locking and idempotency checks.
        Used for Paystack Webhooks, Failed Z9Pay Refunds, and Admin Credits.
        """
        amount = Decimal(str(amount))
        if amount <= Decimal("0.00"):
            raise ValidationError("Credit amount must be greater than zero.")

        # 1. Idempotency Check: Has this reference already been processed?
        existing_entry = WalletLedger.objects.filter(reference=reference).first()
        if existing_entry:
            return existing_entry  # Safely ignore duplicate webhook retries

        # 2. Row Lock: Lock this specific wallet row until the transaction block finishes
        wallet = Wallet.objects.select_for_update().get(user_id=user_id)

        balance_before = wallet.balance
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

        # 3. Create Immutable Ledger Record
        ledger_entry = WalletLedger.objects.create(
            wallet=wallet,
            reference=reference,
            transaction_type=WalletLedger.TransactionType.CREDIT,
            source=source,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=description,
            metadata=metadata or {},
        )
        return ledger_entry

    @staticmethod
    @transaction.atomic
    def debit_wallet(
        user_id, 
        amount: Decimal, 
        reference: str, 
        source: str, 
        description: str, 
        metadata: dict = None
    ) -> WalletLedger:
        """
        Safely locks and deducts funds from a user's wallet before calling Z9Pay.
        """
        amount = Decimal(str(amount))
        if amount <= Decimal("0.00"):
            raise ValidationError("Debit amount must be greater than zero.")

        # 1. Lock the wallet row FIRST to prevent concurrent double-spending
        wallet = Wallet.objects.select_for_update().get(user_id=user_id)

        if wallet.is_locked:
            raise ValidationError("This wallet is currently frozen. Contact support.")

        # 2. Idempotency Check
        if WalletLedger.objects.filter(reference=reference).exists():
            raise DuplicateTransactionError(f"Transaction reference '{reference}' already exists.")

        # 3. Balance Check
        if wallet.balance < amount:
            raise InsufficientBalanceError("Insufficient wallet balance for this transaction.")

        balance_before = wallet.balance
        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])

        # 4. Create Immutable Ledger Record
        ledger_entry = WalletLedger.objects.create(
            wallet=wallet,
            reference=reference,
            transaction_type=WalletLedger.TransactionType.DEBIT,
            source=source,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=description,
            metadata=metadata or {},
        )
        return ledger_entry