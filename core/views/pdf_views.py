from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from core.models import Export

def invoice_pdf_view(request, export_id):
    export = Export.objects.get(id=export_id)

    # ---- Group items (just like in invoice_view) ----
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

    # ---- Render invoice.html with full context ----
    html_string = render_to_string("core/invoice.html", {
        "export": export,
        "grouped_items": grouped_items,
        "grand_total_qty": grand_total_qty,
        "grand_total_value": grand_total_value,
    })
    
    # ---- PDF response ----
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_{export.invoice_number}.pdf"'

    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)

    return response
