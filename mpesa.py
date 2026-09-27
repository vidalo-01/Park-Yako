"""
M-Pesa Daraja 3.0 integration for Smart Gate.

Credentials are read from environment variables; never hard-code them.
Sandbox:
  https://sandbox.safaricom.co.ke
Production:
  https://api.safaricom.co.ke
"""
import base64
import os
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class MpesaError(Exception):
    pass


def _env(name: str, required=True, default=None):
    value = os.getenv(name, default)
    if required and not value:
        raise MpesaError(f"Missing environment variable: {name}")
    return value


def base_url():
    env = os.getenv("MPESA_ENV", "sandbox").lower()
    if env == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def normalize_phone(phone: str) -> str:
    """Normalize Kenyan mobile numbers to 2547XXXXXXXX / 2541XXXXXXXX."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if digits.startswith("7") and len(digits) == 9:
        return "254" + digits
    if digits.startswith("1") and len(digits) == 9:
        return "254" + digits
    raise MpesaError("Enter a valid Kenyan M-Pesa number, e.g. 0712345678.")


def get_access_token() -> str:
    key = _env("MPESA_CONSUMER_KEY")
    secret = _env("MPESA_CONSUMER_SECRET")
    url = f"{base_url()}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(key, secret), timeout=20)
    if not response.ok:
        raise MpesaError(f"Daraja authentication failed ({response.status_code}).")
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise MpesaError("Daraja did not return an access token.")
    return token


def initiate_stk_push(phone: str, amount: int, account_reference: str, description: str):
    """Initiate an M-Pesa Express prompt and return Daraja's request IDs."""
    if amount < 1:
        raise MpesaError("M-Pesa cannot be initiated for a zero amount.")

    shortcode = _env("MPESA_SHORTCODE")
    passkey = _env("MPESA_PASSKEY")
    callback_url = _env("MPESA_CALLBACK_URL")
    phone = normalize_phone(phone)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_raw = f"{shortcode}{passkey}{timestamp}".encode()
    password = base64.b64encode(password_raw).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": os.getenv("MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline"),
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }

    response = requests.post(
        f"{base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok or data.get("ResponseCode") != "0":
        message = data.get("errorMessage") or data.get("ResponseDescription") or "M-Pesa rejected the STK request."
        raise MpesaError(message)

    checkout_id = data.get("CheckoutRequestID")
    if not checkout_id:
        raise MpesaError("Daraja accepted the request but returned no CheckoutRequestID.")
    return {
        "merchant_request_id": data.get("MerchantRequestID"),
        "checkout_request_id": checkout_id,
        "customer_message": data.get("CustomerMessage", "Check your phone for the M-Pesa prompt."),
    }


def query_stk_status(checkout_request_id: str):
    """Optional recovery/status check when a callback has not arrived."""
    shortcode = _env("MPESA_SHORTCODE")
    passkey = _env("MPESA_PASSKEY")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    response = requests.post(
        f"{base_url()}/mpesa/stkpushquery/v1/query",
        json=payload,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=30,
    )
    try:
        return response.json()
    except ValueError:
        return {"ResponseDescription": "Invalid response from Daraja."}
