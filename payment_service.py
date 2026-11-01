"""
Custom UPI Payment Service
--------------------------
Handles Master Google Pay UPI ID configuration,
dynamic UPI QR code generation, and payment payload generation
according to NPCI UPI specifications (upi://pay?pa=...).
"""

import io
import re
import base64
import urllib.parse
import qrcode
from firebase_service import FirestoreRepository

# UPI ID validation pattern (e.g., name@okhdfcbank, store@upi, 9876543210@paytm)
UPI_REGEX = re.compile(r"^[\w.\-_]{2,256}@[a-zA-Z]{2,64}$")


def get_master_upi_id():
    """Retrieve the master Google Pay UPI ID configured by the admin."""
    return FirestoreRepository.get_setting("master_upi_id", "merchant@okhdfcbank")


def get_merchant_name():
    """Retrieve the business/merchant display name for UPI payments."""
    return FirestoreRepository.get_setting("merchant_name", "AI Style Fashion Store")


def update_master_upi_config(upi_id, merchant_name=None):
    """
    Validate and persist master UPI ID and merchant name.
    """
    cleaned_upi = (upi_id or "").strip()
    if not cleaned_upi:
        raise ValueError("UPI ID cannot be empty.")

    if not UPI_REGEX.match(cleaned_upi):
        raise ValueError("Invalid UPI ID format. Standard format: username@bank (e.g. store@okhdfcbank)")

    FirestoreRepository.set_setting("master_upi_id", cleaned_upi)

    if merchant_name:
        FirestoreRepository.set_setting("merchant_name", merchant_name.strip())

    return True


def generate_upi_payload(upi_id=None, payee_name=None, amount=0.0, order_id=None, note=None):
    """
    Generate standard NPCI UPI URI payload.
    Format: upi://pay?pa=...&pn=...&am=...&cu=INR&tn=...&tr=...
    """
    active_upi = upi_id or get_master_upi_id()
    active_name = payee_name or get_merchant_name()

    try:
        numeric_amount = f"{float(amount):.2f}"
    except (ValueError, TypeError):
        numeric_amount = "0.00"

    params = {
        "pa": active_upi,
        "pn": active_name,
        "am": numeric_amount,
        "cu": "INR"
    }

    if note:
        params["tn"] = note
    elif order_id:
        params["tn"] = f"AI Style Order {order_id}"
    else:
        params["tn"] = "Clothing Order"

    if order_id:
        params["tr"] = str(order_id)

    query_string = urllib.parse.urlencode(params)
    return f"upi://pay?{query_string}"


def generate_upi_qr_base64(upi_payload):
    """
    Render a dynamic QR code for the given UPI URI payload.
    Returns a data URI string (data:image/png;base64,...) ready for inline HTML <img> rendering.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(upi_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#111111", back_color="#ffffff")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"


def generate_order_upi_qr(order_id, amount, payee_name=None):
    """
    Convenience method: generates both payload and base64 QR code for a given order.
    """
    upi_id = get_master_upi_id()
    name = payee_name or get_merchant_name()
    payload = generate_upi_payload(
        upi_id=upi_id,
        payee_name=name,
        amount=amount,
        order_id=order_id,
        note=f"Pay for {order_id}"
    )
    qr_base64 = generate_upi_qr_base64(payload)
    return {
        "upi_id": upi_id,
        "payee_name": name,
        "amount": f"{float(amount):.2f}",
        "payload": payload,
        "qr_base64": qr_base64
    }

