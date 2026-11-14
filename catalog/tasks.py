from decimal import Decimal
from celery import shared_task
from z9pay_integration.client import Z9PayClient
from .models import Network, DataPlan


@shared_task
def sync_catalog_from_z9pay(default_markup_naira: str = "30.00"):
    """
    Fetches networks from GET /data/networks/ and plans from GET /data/networks/{id}/plans/
    and updates our local database cost prices.
    """
    markup = Decimal(default_markup_naira)
    networks = Z9PayClient.get_data_networks()

    for net_data in networks:
        net_id = str(net_data.get("id"))
        net_name = net_data.get("name", "")
        net_code = net_data.get("code", net_name).upper()

        network_obj, _ = Network.objects.update_or_create(
            z9pay_network_id=net_id,
            defaults={"name": net_name, "code": net_code},
        )

        # Now fetch GET /data/networks/{id}/plans/ for this network
        plans = Z9PayClient.get_network_data_plans(net_id)
        for plan_data in plans:
            plan_code = str(plan_data.get("id") or plan_data.get("plan_code"))
            plan_name = plan_data.get("name") or plan_data.get("plan_name", "Data Bundle")
            cost_price = Decimal(str(plan_data.get("price") or plan_data.get("amount", "0.00")))
            validity = plan_data.get("validity", "30 Days")

            existing_plan = DataPlan.objects.filter(z9pay_plan_code=plan_code).first()
            if existing_plan:
                # Update cost_price if Z9Pay changed their price; ensure selling_price stays profitable
                existing_plan.cost_price = cost_price
                if existing_plan.selling_price <= cost_price:
                    existing_plan.selling_price = cost_price + markup
                existing_plan.save(update_fields=["cost_price", "selling_price", "updated_at"])
            else:
                DataPlan.objects.create(
                    network=network_obj,
                    name=plan_name,
                    validity=validity,
                    z9pay_plan_code=plan_code,
                    cost_price=cost_price,
                    selling_price=cost_price + markup,
                )