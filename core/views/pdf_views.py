from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from core.models import Export
from collections import defaultdict
from decimal import Decimal

# ===========================
# Invoice PDF (all items)
# ===========================


def invoice_pdf_view(request, export_id):
    export = Export.objects.get(id=export_id)

    # Grouped data container
    grouped = defaultdict(lambda: {
        "total_qty": 0,
        "total_value": Decimal("0.00"),
    })

    # Group by (box, pallet, cross_ref, price, PO, PO line)
    for item in export.items.all():
        key = (
            item.box_number,
            item.pallet_number,
            item.cross_reference,
            item.price,
            item.customer_po,
            item.po_line,
        )
        grouped[key]["total_qty"] += item.qty or 0
        grouped[key]["total_value"] += (item.price or 0) * (item.qty or 0)

    # Convert into list for template
    grouped_items = []
    grand_total_qty = 0
    grand_total_value = Decimal("0.00")

    for (box, pallet, cross_ref, price, customer_po, po_line), values in grouped.items():
        grouped_items.append({
            "box_number": box,
            "pallet_number": pallet,
            "cross_reference": cross_ref,
            "price": price,
            "customer_po": customer_po,
            "po_line": po_line,
            "total_qty": values["total_qty"],
            "total_value": values["total_value"],
        })
        grand_total_qty += values["total_qty"]
        grand_total_value += values["total_value"]

    # ---- Render invoice template ----
    html_string = render_to_string("core/invoice.html", {
        "export": export,
        "grouped_items": grouped_items,
        "grand_total_qty": grand_total_qty,
        "grand_total_value": grand_total_value,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_{export.invoice_number}.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response


# ===========================
# Packing List PDF (all items)
# ===========================
from collections import defaultdict
from decimal import Decimal

def packing_list_pdf_view(request, export_id):
    export = Export.objects.get(id=export_id)

    # Grouped data container
    grouped = defaultdict(lambda: {
        "total_qty": 0,
    })

    # Group by (box, pallet, PN, Customer PO, PO line)
    for item in export.items.all():
        key = (
            item.box_number,
            item.pallet_number,
            item.cross_reference,
            item.customer_po,
            item.po_line,
        )
        grouped[key]["description"] = item.description
        grouped[key]["total_qty"] += item.qty or 0

    # Convert into list for template
    grouped_items = []
    for (box, pallet, cross_ref, customer_po, po_line), values in grouped.items():
        grouped_items.append({
            "box_number": box,
            "pallet_number": pallet,
            "cross_reference": cross_ref,
            "customer_po": customer_po,
            "po_line": po_line,
            "description": values["description"],
            "total_qty": values["total_qty"],
        })

    pallets = export.pallets.all()

    # ---- Render template ----
    html_string = render_to_string("core/packing_list.html", {
        "export": export,
        "items": grouped_items,   # now grouped
        "pallets": pallets,
        "total_gross_weight": export.total_gross_weight,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="PackingList_{export.packing_list_number}.pdf"'
    )
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response





# ===========================
# Invoice PDF (per pallet)
# ===========================
from collections import defaultdict
from decimal import Decimal

def invoice_pdf_per_pallet_view(request, export_id, pallet_id):
    export = Export.objects.get(id=export_id)
    pallet = export.pallets.get(id=pallet_id)

    # Filter only items for this pallet
    items = export.items.filter(pallet_number=pallet.pallet_number)

    grouped = defaultdict(lambda: {"total_qty": 0, "total_value": Decimal("0.00")})

    for item in items:
        key = (
            item.box_number,
            item.pallet_number,
            item.cross_reference,
            item.price,
            item.customer_po,
            item.po_line,
        )
        grouped[key]["description"] = item.description
        grouped[key]["total_qty"] += item.qty or 0
        grouped[key]["total_value"] += (item.price or 0) * (item.qty or 0)

    grouped_items = []
    grand_total_qty = 0
    grand_total_value = Decimal("0.00")

    for (box, pallet_no, cross_ref, price, customer_po, po_line), values in grouped.items():
        grouped_items.append({
            "box_number": box,
            "pallet_number": pallet_no,
            "cross_reference": cross_ref,
            "price": price,
            "customer_po": customer_po,
            "po_line": po_line,
            "description": values["description"],
            "total_qty": values["total_qty"],
            "total_value": values["total_value"],
        })
        grand_total_qty += values["total_qty"]
        grand_total_value += values["total_value"]

    html_string = render_to_string("core/invoice.html", {
        "export": export,
        "grouped_items": grouped_items,
        "grand_total_qty": grand_total_qty,
        "grand_total_value": grand_total_value,
        "pallet": pallet,  # optional: show header note
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Invoice_{export.invoice_number}_Pallet{pallet.pallet_number}.pdf"'
    )
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response



# ===========================
# Packing List PDF (per pallet)
# ===========================
def packing_list_pdf_per_pallet_view(request, export_id, pallet_id):
    export = Export.objects.get(id=export_id)
    pallet = export.pallets.get(id=pallet_id)

    # Filter only items for this pallet
    items = export.items.filter(pallet_number=pallet.pallet_number)

    grouped = defaultdict(lambda: {"total_qty": 0})

    for item in items:
        key = (
            item.box_number,
            item.pallet_number,
            item.cross_reference,
            item.customer_po,
            item.po_line,
        )
        grouped[key]["description"] = item.description
        grouped[key]["total_qty"] += item.qty or 0

    grouped_items = []
    for (box, pallet_no, cross_ref, customer_po, po_line), values in grouped.items():
        grouped_items.append({
            "box_number": box,
            "pallet_number": pallet_no,
            "cross_reference": cross_ref,
            "customer_po": customer_po,
            "po_line": po_line,
            "description": values["description"],
            "total_qty": values["total_qty"],
        })

    html_string = render_to_string("core/packing_list.html", {
        "export": export,
        "items": grouped_items,
        "pallets": [pallet],  # only this pallet
        "total_gross_weight": pallet.gross_weight_kg,
        "pallet": pallet,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="PackingList_{export.packing_list_number}_Pallet{pallet.pallet_number}.pdf"'
    )
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response
