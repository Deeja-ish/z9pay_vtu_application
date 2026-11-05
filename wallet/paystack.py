import hmac
import hashlib
import requests
from django.conf import settings


class PaystackClient:
    BASE_URL = "https://api.paystack.co"

    @classmethod
    def _headers(cls):
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @classmethod
    def assign_dedicated_virtual_account(cls, user):
        """
        Single-step API call to create a Paystack Customer and assign a Dedicated Virtual Account.
        Paystack sends 'dedicatedaccount.assign.success' to our webhook once ready.
        """
        url = f"{cls.BASE_URL}/dedicated_account/assign"
        payload = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone_number,
            "preferred_bank": getattr(settings, "PAYSTACK_PREFERRED_BANK", "wema-bank"),
            "country": "NG",
        }
        response = requests.post(url, json=payload, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
        """
        Verifies the x-paystack-signature header using HMAC SHA512.
        """
        if not signature_header:
            return False
        computed_hash = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(computed_hash, signature_header)