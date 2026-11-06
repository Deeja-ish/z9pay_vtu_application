import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from .paystack import PaystackClient

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        # 1. Create the empty wallet in our database
        Wallet.objects.create(user=instance)

        # 2. Request a Dedicated Virtual Account from Paystack
        if not settings.PAYSTACK_SECRET_KEY.startswith("sk_test_dummy"):
            try:
                PaystackClient.assign_dedicated_virtual_account(instance)
            except Exception as e:
                # We log the error rather than crashing user registration if Paystack is down
                logger.error(f"Failed to assign Paystack DVA for {instance.email}: {e}")