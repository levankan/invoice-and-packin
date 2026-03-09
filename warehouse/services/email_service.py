from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from admin_area.models import DeliveryEmailConfiguration
from imports.models import ImportLine


def send_delivery_email(import_obj):
    config = DeliveryEmailConfiguration.objects.filter(is_active=True).first()

    if not config:
        return

    to_list = [e.strip() for e in config.email_to.split(",") if e.strip()]
    cc_list = [e.strip() for e in config.cc.split(",") if e.strip()] if config.cc else []
    bcc_list = [e.strip() for e in config.bcc.split(",") if e.strip()] if config.bcc else []

    import_code = getattr(import_obj, "import_code", "N/A")
    tracking_no = getattr(import_obj, "tracking_no", "N/A")
    vendor_reference = getattr(import_obj, "vendor_reference", "N/A")
    received_at = getattr(import_obj, "received_at", None)
    received_by = getattr(import_obj, "received_by", None)

    received_at_value = received_at.strftime("%Y-%m-%d %H:%M") if received_at else "N/A"

    if received_by:
        if hasattr(received_by, "get_full_name"):
            received_by_value = received_by.get_full_name() or received_by.username
        else:
            received_by_value = str(received_by)
    else:
        received_by_value = "N/A"

    subject = config.email_subject or f"Shipment Delivered: {import_code}"

    # Get related import lines
    lines = ImportLine.objects.filter(import_header=import_obj)

    # Plain text fallback
    text_body = f"""
{config.email_text}

Import Code: {import_code}
Tracking Number: {tracking_no}
Vendor Reference: {vendor_reference}
Received At: {received_at_value}
Received By: {received_by_value}
"""

    # Build HTML rows
    table_rows = ""
    for line in lines:
        document_no = getattr(line, "document_no", "") or ""
        line_no = getattr(line, "line_no", "") or ""
        item_no = getattr(line, "item_no", "") or ""
        description = getattr(line, "description", "") or ""
        quantity = getattr(line, "quantity", "") or ""
        uom = getattr(line, "unit_of_measure", "") or getattr(line, "uom", "") or ""

        table_rows += f"""
        <tr>
            <td>{document_no}</td>
            <td>{line_no}</td>
            <td>{item_no}</td>
            <td>{description}</td>
            <td>{quantity}</td>
            <td>{uom}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #222;">
        <p>{config.email_text}</p>

        <p><strong>Import Code:</strong> {import_code}</p>
        <p><strong>Tracking Number:</strong> {tracking_no}</p>
        <p><strong>Vendor Reference:</strong> {vendor_reference}</p>
        <p><strong>Received At:</strong> {received_at_value}</p>
        <p><strong>Received By:</strong> {received_by_value}</p>

        <br>

        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <thead style="background-color: #f2f2f2;">
                <tr>
                    <th>Document No</th>
                    <th>Line No</th>
                    <th>Item No</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>UOM</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </body>
    </html>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_list,
        cc=cc_list,
        bcc=bcc_list,
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)