from django.core.mail import EmailMessage
from django.conf import settings
from .models import DeliveryEmailConfiguration


def send_delivery_email(import_obj):
    config = DeliveryEmailConfiguration.objects.filter(is_active=True).first()

    if not config:
        return

    to_list = [e.strip() for e in config.email_to.split(",") if e.strip()]
    cc_list = [e.strip() for e in config.cc.split(",") if e.strip()] if config.cc else []
    bcc_list = [e.strip() for e in config.bcc.split(",") if e.strip()] if config.bcc else []

    received_at = getattr(import_obj, "received_at", None)
    received_by = getattr(import_obj, "received_by", None)
    vendor_reference = getattr(import_obj, "vendor_reference", "")
    tracking_no = getattr(import_obj, "tracking_no", "")
    import_code = getattr(import_obj, "import_code", "")

    if received_by:
        if hasattr(received_by, "get_full_name"):
            received_by_value = received_by.get_full_name() or received_by.username
        else:
            received_by_value = str(received_by)
    else:
        received_by_value = "N/A"

    received_at_value = received_at.strftime("%Y-%m-%d %H:%M") if received_at else "N/A"

    subject = f"Shipment Delivered: {import_code}"

    message = f"""
{config.email_text}

Import Code: {import_code}
Tracking Number: {tracking_no}
Vendor Reference: {vendor_reference}
Received At: {received_at_value}
Received By: {received_by_value}
"""

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_list,
        cc=cc_list,
        bcc=bcc_list,
    )
    email.send(fail_silently=False)