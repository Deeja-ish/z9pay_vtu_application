import uuid
import requests
from django.conf import settings


class Z9PayClient:
    """
    Isolated service layer communicating with the official Z9Pay Developer API.
    """

    @classmethod
    def _headers(cls):
        return {
            "Authorization": f"Bearer {settings.Z9PAY_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @classmethod
    def get_profile(cls) -> dict:
        """GET /profile/ -> Get developer profile & Z9Pay wallet balance."""
        url = f"{settings.Z9PAY_BASE_URL.rstrip('/')}/profile/"
        response = requests.get(url, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        return response.json()

    @classmethod
    def get_data_networks(cls) -> list:
        """GET /data/networks/ -> List data networks from Z9Pay."""
        url = f"{settings.Z9PAY_BASE_URL.rstrip('/')}/data/networks/"
        response = requests.get(url, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("data", data) if isinstance(data, dict) else data

    @classmethod
    def get_network_data_plans(cls, z9pay_network_id: str) -> list:
        """GET /data/networks/{id}/plans/ -> Data plans for a specific network."""
        url = f"{settings.Z9PAY_BASE_URL.rstrip('/')}/data/networks/{z9pay_network_id}/plans/"
        response = requests.get(url, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("data", data) if isinstance(data, dict) else data

    @classmethod
    def verify_purchase(cls, reference: str) -> dict:
        """GET /verify/{reference}/ -> Verify purchase status on Z9Pay."""
        url = f"{settings.Z9PAY_BASE_URL.rstrip('/')}/verify/{reference}/"
        response = requests.get(url, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        return response.json()

    @classmethod
    def purchase_data(cls, network_id: str, plan_code: str, phone_number: str, reference: str) -> dict:
        """
        POST /purchase/ -> Create a data purchase on Z9Pay.
        Returns a standardized dict:
        {
            "status": "SUCCESS" | "FAILED" | "PENDING",
            "upstream_reference": "...",
            "message": "...",
            "raw_response": {...}
        }
        """
        # --- LOCAL SANDBOX / MOCK MODE FOR POSTMAN TESTING ---
        if getattr(settings, "Z9PAY_MOCK_MODE", False):
            if phone_number.endswith("0000"):
                return {
                    "status": "FAILED",
                    "upstream_reference": f"Z9P_FAIL_{uuid.uuid4().hex[:8].upper()}",
                    "message": "Simulated Z9Pay Failure: Upstream network unavailable for numbers ending in 0000.",
                    "raw_response": {"mock": True, "endpoint": "/purchase/", "status": "failed"},
                }
            return {
                "status": "SUCCESS",
                "upstream_reference": f"Z9P_OK_{uuid.uuid4().hex[:8].upper()}",
                "message": f"Successfully delivered {plan_code} to {phone_number}.",
                "raw_response": {"mock": True, "endpoint": "/purchase/", "status": "success", "reference": reference},
            }

        # --- LIVE Z9PAY HTTP CALL (POST /purchase/) ---
        url = f"{settings.Z9PAY_BASE_URL.rstrip('/')}/purchase/"
        payload = {
            "service_type": "data",
            "network": network_id,
            "plan": plan_code,
            "phone_number": phone_number,
            "reference": reference,
        }

        try:
            response = requests.post(url, json=payload, headers=cls._headers(), timeout=30)
            data = response.json()

            tx_status = str(data.get("status", "")).upper()
            if response.status_code in [200, 201] and tx_status in ["SUCCESS", "SUCCESSFUL", "COMPLETED", "TRUE"]:
                return {
                    "status": "SUCCESS",
                    "upstream_reference": str(data.get("reference") or data.get("id") or ""),
                    "message": data.get("message", "Data purchase successful"),
                    "raw_response": data,
                }
            elif response.status_code in [400, 422] or tx_status in ["FAILED", "ERROR", "FALSE"]:
                return {
                    "status": "FAILED",
                    "upstream_reference": str(data.get("reference") or data.get("id") or ""),
                    "message": data.get("message", "Z9Pay rejected the transaction"),
                    "raw_response": data,
                }
            else:
                return {
                    "status": "PENDING",
                    "upstream_reference": str(data.get("reference") or data.get("id") or ""),
                    "message": "Transaction still processing on Z9Pay",
                    "raw_response": data,
                }

        except requests.exceptions.Timeout:
            # Never auto-refund on timeout; use GET /verify/{reference}/ to confirm!
            return {
                "status": "PENDING",
                "upstream_reference": "",
                "message": "Request to Z9Pay timed out. Pending verification via /verify/{reference}/.",
                "raw_response": {"error": "Timeout"},
            }
        except requests.exceptions.RequestException as exc:
            return {
                "status": "PENDING",
                "upstream_reference": "",
                "message": f"Network error: {str(exc)}",
                "raw_response": {"error": str(exc)},
            }