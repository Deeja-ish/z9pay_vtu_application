import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Network(models.Model):
    class NetworkCode(models.TextChoices):
        MTN = "MTN", "MTN Nigeria"
        AIRTEL = "AIRTEL", "Airtel Nigeria"
        GLO = "GLO", "Globacom (Glo)"
        NINE_MOBILE = "9MOBILE", "9mobile"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, choices=NetworkCode.choices, unique=True, db_index=True)
    
    # Upstream Z9Pay identifier for this network (if Z9Pay uses network IDs like "1" or "mtn")
    z9pay_network_id = models.CharField(max_length=50, help_text="Network code/ID expected by Z9Pay API.")
    
    # Circuit Breaker: Allows the Admin to hide an entire network if MTN/Airtel is down
    is_active = models.BooleanField(default=True, help_text="Uncheck to temporarily hide this network from users.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        status = "Active" if self.is_active else "Offline"
        return f"{self.name} ({status})"


class DataPlan(models.Model):
    class PlanCategory(models.TextChoices):
        SME = "SME", "SME Data"
        CORPORATE = "CORPORATE", "Corporate Gifting"
        DIRECT = "DIRECT", "Direct Gifting"
        AWOOF = "AWOOF", "Awoof / Special"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="plans")
    
    name = models.CharField(max_length=100, help_text="e.g., 1GB SME Monthly")
    category = models.CharField(max_length=20, choices=PlanCategory.choices, default=PlanCategory.SME)
    validity = models.CharField(max_length=50, help_text="e.g., 30 Days, 7 Days, 1 Day")
    
    # Upstream mapping to Z9Pay
    z9pay_plan_code = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="The exact plan_id / product_code required by the Z9Pay API."
    )
    
    # Pricing & Profit Margin
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="How much Z9Pay charges us."
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="How much the customer pays in the app."
    )
    
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this specific plan from users.")
    sort_order = models.PositiveIntegerField(default=0, help_text="Controls the display order in the app.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "selling_price"]

    @property
    def profit_margin(self) -> Decimal:
        return self.selling_price - self.cost_price

    def __str__(self):
        return f"{self.network.code} - {self.name} (₦{self.selling_price})"
