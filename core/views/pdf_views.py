from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from core.models import Export


# ===========================
# Invoice PDF (all items)
# ===========================
def invoice_pdf_view(request, export_id):
    export = Export.objects.get(id=export_id)

    grouped_items = []
    grand_total_qty = 0
    grand_total_value = 0

    for item in export.items.all():
        total_value = (item.price or 0) * (item.qty or 0)
        grouped_items.append({
            "customer_po": item.customer_po,
            "po_line": item.po_line,
            "cross_reference": item.cross_reference,
            "description": item.description,
            "price": item.price,
            "total_qty": item.qty,
            "total_value": total_value,
        })
        grand_total_qty += item.qty or 0
        grand_total_value += total_value

    html_string = render_to_string("core/invoice.html", {
        "export": export,
        "grouped_items": grouped_items,
        "grand_total_qty": grand_total_qty,
        "grand_total_value": grand_total_value,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Invoice_{export.invoice_number}.pdf"'
    )
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response


# ===========================
# Packing List PDF (all items)
# ===========================
def packing_list_pdf_view(request, export_id):
    export = Export.objects.get(id=export_id)

    items = export.items.all()
    pallets = export.pallets.all()
    total_gross_weight = export.total_gross_weight

    html_string = render_to_string("core/packing_list.html", {
        "export": export,
        "items": items,
        "pallets": pallets,
        "total_gross_weight": total_gross_weight,
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
def invoice_pdf_per_pallet_view(request, export_id, pallet_id):
    export = Export.objects.get(id=export_id)
    pallet = export.pallets.get(id=pallet_id)

    items = export.items.filter(pallet_number=pallet.pallet_number)

    grouped_items = []
    grand_total_qty = 0
    grand_total_value = 0

    for item in items:
        total_value = (item.price or 0) * (item.qty or 0)
        grouped_items.append({
            "customer_po": item.customer_po,
            "po_line": item.po_line,
            "cross_reference": item.cross_reference,
            "description": item.description,
            "price": item.price,
            "total_qty": item.qty,
            "total_value": total_value,
        })
        grand_total_qty += item.qty or 0
        grand_total_value += total_value

    html_string = render_to_string("core/invoice.html", {
        "export": export,
        "grouped_items": grouped_items,
        "grand_total_qty": grand_total_qty,
        "grand_total_value": grand_total_value,
        "pallet": pallet,  # shows "Filtered by Pallet X"
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

    items = export.items.filter(pallet_number=pallet.pallet_number)

    html_string = render_to_string("core/packing_list.html", {
        "export": export,
        "items": items,
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
