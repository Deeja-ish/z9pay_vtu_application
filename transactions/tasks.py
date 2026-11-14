from celery import shared_task
from django.db import transaction
from wallet.models import WalletLedger
from wallet.services import WalletService
from z9pay_integration.client import Z9PayClient
from .models import DataTransaction


@shared_task
def process_z9pay_data_purchase(transaction_id: str):
    """
    Asynchronous Celery task that calls Z9Pay and reconciles the transaction.
    If Z9Pay fails, it automatically refunds the user's wallet.
    """
    try:
        tx = DataTransaction.objects.select_related("plan__network", "user").get(id=transaction_id)
    except DataTransaction.DoesNotExist:
        return

    # Guard against double-processing if a task is ever retried
    if tx.status != DataTransaction.Status.PENDING:
        return

    # 1. Call the isolated Z9Pay client
    result = Z9PayClient.purchase_data(
        network_id=tx.plan.network.z9pay_network_id,
        plan_code=tx.plan.z9pay_plan_code,
        phone_number=tx.phone_number,
        reference=tx.reference,
    )

    # 2. Reconcile status & issue automatic refund if Z9Pay failed
    with transaction.atomic():
        # Lock the transaction row so two workers or an admin can't refund it simultaneously
        tx = DataTransaction.objects.select_for_update().get(id=transaction_id)
        if tx.status != DataTransaction.Status.PENDING:
            return

        tx.z9pay_reference = result.get("upstream_reference", "")
        tx.response_message = result.get("message", "")
        tx.z9pay_raw_response = result.get("raw_response", {})

        if result["status"] == "SUCCESS":
            tx.status = DataTransaction.Status.SUCCESS
            tx.save()

        elif result["status"] == "FAILED":
            tx.status = DataTransaction.Status.REFUNDED
            tx.save()

            # Automatically refund the exact deducted amount back to the user's wallet!
            WalletService.credit_wallet(
                user_id=tx.user_id,
                amount=tx.amount_charged,
                reference=f"REFUND-{tx.reference}",
                source=WalletLedger.SourceType.PURCHASE_REFUND,
                description=f"Auto-refund for failed data purchase ({tx.plan.name} to {tx.phone_number})",
                metadata={"original_reference": tx.reference},
            )
        else:
            # Remains PENDING (e.g., on timeout) so the admin can verify or requery
            tx.save()

@shared_task
def verify_pending_z9pay_transaction(transaction_id: str):
    """
    Calls GET /verify/{reference}/ on Z9Pay to resolve a stuck PENDING transaction.
    """
    try:
        tx = DataTransaction.objects.get(id=transaction_id)
    except DataTransaction.DoesNotExist:
        return

    if tx.status != DataTransaction.Status.PENDING:
        return

    try:
        verification_data = Z9PayClient.verify_purchase(tx.reference)
    except Exception:
        return

    remote_status = str(verification_data.get("status", "")).upper()

    with transaction.atomic():
        tx = DataTransaction.objects.select_for_update().get(id=transaction_id)
        if tx.status != DataTransaction.Status.PENDING:
            return

        tx.z9pay_raw_response = verification_data
        if remote_status in ["SUCCESS", "SUCCESSFUL", "COMPLETED"]:
            tx.status = DataTransaction.Status.SUCCESS
            tx.response_message = "Verified successful via Z9Pay /verify/ endpoint."
            tx.save()
        elif remote_status in ["FAILED", "REVERSED"]:
            tx.status = DataTransaction.Status.REFUNDED
            tx.response_message = "Verified failed via Z9Pay /verify/ endpoint. Wallet refunded."
            tx.save()

            WalletService.credit_wallet(
                user_id=tx.user_id,
                amount=tx.amount_charged,
                reference=f"REFUND-{tx.reference}",
                source=WalletLedger.SourceType.PURCHASE_REFUND,
                description=f"Auto-refund after Z9Pay verification failed ({tx.reference})",
                metadata={"original_reference": tx.reference},
            )