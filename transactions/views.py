from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from wallet.models import WalletLedger
from wallet.services import WalletService, InsufficientBalanceError, DuplicateTransactionError
from .models import DataTransaction
from .serializers import DataPurchaseInputSerializer, DataTransactionSerializer
from .tasks import process_z9pay_data_purchase


class PurchaseDataView(APIView):
    """
    POST /api/v1/purchase/data/
    1. Validates request & checks idempotency.
    2. Locks wallet, deducts selling_price, and creates PENDING transaction.
    3. Dispatches Celery task to Z9Pay.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DataPurchaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data["plan_id"]  # Returns the validated DataPlan object
        phone_number = serializer.validated_data["phone_number"]
        reference = serializer.validated_data["reference"]

        # 1. Idempotency Check: If client retries the exact same reference, return the existing transaction!
        existing_tx = DataTransaction.objects.filter(reference=reference, user=request.user).first()
        if existing_tx:
            return Response(
                DataTransactionSerializer(existing_tx).data, 
                status=status.HTTP_200_OK
            )

        # 2. Synchronous Lock, Wallet Deduction & PENDING Transaction Creation
        try:
            with transaction.atomic():
                WalletService.debit_wallet(
                    user_id=request.user.id,
                    amount=plan.selling_price,
                    reference=f"PURCHASE-{reference}",
                    source=WalletLedger.SourceType.DATA_PURCHASE,
                    description=f"Data Purchase: {plan.network.code} {plan.name} for {phone_number}",
                    metadata={"phone_number": phone_number, "plan_id": str(plan.id)},
                )

                data_tx = DataTransaction.objects.create(
                    user=request.user,
                    plan=plan,
                    phone_number=phone_number,
                    reference=reference,
                    amount_charged=plan.selling_price,
                    cost_price=plan.cost_price,
                    status=DataTransaction.Status.PENDING,
                    response_message="Transaction queued for fulfillment.",
                )
        except InsufficientBalanceError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (DuplicateTransactionError, ValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Asynchronous Dispatch to Z9Pay Worker
        process_z9pay_data_purchase.delay(str(data_tx.id))

        # Refresh from DB in case CELERY_TASK_ALWAYS_EAGER=True updated it synchronously during local testing
        data_tx.refresh_from_db()

        return Response(
            DataTransactionSerializer(data_tx).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionListView(generics.ListAPIView):
    """GET /api/v1/transactions/ -> Paginated purchase history for the logged-in user."""
    serializer_class = DataTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DataTransaction.objects.select_related("plan__network").filter(user=self.request.user)


class TransactionDetailView(generics.RetrieveAPIView):
    """GET /api/v1/transactions/<reference>/ -> Check status of a specific purchase."""
    serializer_class = DataTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "reference"

    def get_queryset(self):
        return DataTransaction.objects.select_related("plan__network").filter(user=self.request.user)