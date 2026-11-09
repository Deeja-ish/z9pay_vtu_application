from django.contrib import admin
from .models import Network, DataPlan


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "z9pay_network_id", "is_active", "updated_at"]
    list_editable = ["is_active"]  # Admin can toggle networks on/off right from the list view!
    search_fields = ["name", "code"]


@admin.register(DataPlan)
class DataPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "network",
        "category",
        "validity",
        "z9pay_plan_code",
        "cost_price",
        "selling_price",
        "display_profit",
        "is_active",
    ]
    list_filter = ["network", "category", "is_active"]
    list_editable = ["selling_price", "is_active"]  # Admin can edit prices & toggle plans inline!
    search_fields = ["name", "z9pay_plan_code"]

    @admin.display(description="Profit Margin (₦)")
    def display_profit(self, obj):
        return f"₦{obj.profit_margin}"