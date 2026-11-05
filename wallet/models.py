import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="wallet"
    )
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    
    # Paystack Customer & Dedicated Virtual Account (DVA) Fields
    paystack_customer_code = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    account_name = models.CharField(max_length=150, blank=True, null=True)

    is_locked = models.BooleanField(default=False, help_text="Freeze wallet if suspicious activity is detected.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.phone_number} - ₦{self.balance}"


class WalletLedger(models.Model):
    class TransactionType(models.TextChoices):
        CREDIT = "CREDIT", "Credit (Money In)"
        DEBIT = "DEBIT", "Debit (Money Out)"

    class SourceType(models.TextChoices):
        PAYSTACK_DVA = "PAYSTACK_DVA", "Bank Transfer (Virtual Account)"
        PAYSTACK_CARD = "PAYSTACK_CARD", "Card / USSD Checkout"
        DATA_PURCHASE = "DATA_PURCHASE", "Data Bundle Purchase"
        PURCHASE_REFUND = "PURCHASE_REFUND", "Failed Purchase Refund"
        ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT", "Admin Manual Adjustment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="ledger_entries")
    
    # Idempotency key: Ensures the exact same payment/purchase is NEVER processed twice
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    source = models.CharField(max_length=30, choices=SourceType.choices)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    description = models.CharField(max_length=255, help_text="Reason for the transaction (mandatory for Admin adjustments).")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.transaction_type}] ₦{self.amount} - Ref: {self.reference}"