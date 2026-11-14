import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from catalog.models import DataPlan


class DataTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Failed & Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="data_transactions"
    )
    plan = models.ForeignKey(
        DataPlan, 
        on_delete=models.PROTECT, 
        related_name="transactions"
    )
    
    phone_number = models.CharField(max_length=15, db_index=True)
    
    # Client-generated idempotency reference
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    # Reference returned by Z9Pay
    z9pay_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial snapshots at the exact moment of purchase
    amount_charged = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(
        max_length=15, 
        choices=Status.choices, 
        default=Status.PENDING, 
        db_index=True
    )
    response_message = models.CharField(max_length=255, blank=True, null=True)
    z9pay_raw_response = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def profit(self) -> Decimal:
        if self.status == self.Status.SUCCESS:
            return self.amount_charged - self.cost_price
        return Decimal("0.00")

    def __str__(self):
        return f"{self.reference} | {self.phone_number} | {self.plan.name} | {self.status}"