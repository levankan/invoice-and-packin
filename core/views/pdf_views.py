from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from core.models import Export
from collections import defaultdict
from decimal import Decimal
import qrcode
import base64
from io import BytesIO
from core.models import Export, Pallet
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from weasyprint import HTML
from django.contrib.auth.decorators import login_required
from core.models import Export, Pallet
import qrcode
import base64
from io import BytesIO
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from weasyprint import HTML
from django.contrib.auth.decorators import login_required
from core.models import Export, Pallet
import barcode
from barcode.writer import ImageWriter
import base64
from io import BytesIO



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
        grouped[key]["description"] = item.description

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
            "description": values["description"], 
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


def packing_list_pdf_view(request, export_id):
    export = Export.objects.get(id=export_id)

    grouped = defaultdict(lambda: {"total_qty": 0})

    # Group by same keys as invoice (include price for consistency)
    for item in export.items.all():
        key = (
            item.box_number,
            item.pallet_number,
            item.cross_reference,
            item.price,          # ✅ added to match invoice grouping
            item.customer_po,
            item.po_line,
        )
        grouped[key]["description"] = item.description
        grouped[key]["total_qty"] += item.qty or 0
        grouped[key]["price"] = item.price   # ✅ store but we don’t use in total $

    grouped_items = []
    grand_total_qty = 0

    for (box, pallet_no, cross_ref, price, customer_po, po_line), values in grouped.items():
        grouped_items.append({
            "box_number": box,
            "pallet_number": pallet_no,
            "cross_reference": cross_ref,
            "customer_po": customer_po,
            "po_line": po_line,
            "description": values["description"],
            "price": price,   # ✅ optional, for display only
            "total_qty": values["total_qty"],
        })
        grand_total_qty += values["total_qty"]

    html_string = render_to_string("core/packing_list.html", {
        "export": export,
        "items": grouped_items,
        "pallets": export.pallets.all(),
        "total_gross_weight": sum(p.gross_weight_kg for p in export.pallets.all()),
        "grand_total_qty": grand_total_qty,
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
    f'attachment; filename="Invoice_{export.invoice_number}_{pallet.pallet_number}.pdf"'
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
    grand_total_qty = 0
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
        grand_total_qty += values["total_qty"]

    html_string = render_to_string("core/packing_list.html", {
        "export": export,
        "items": grouped_items,
        "pallets": [pallet],  # only this pallet
        "total_gross_weight": pallet.gross_weight_kg,
        "grand_total_qty": grand_total_qty,
        "pallet": pallet,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="PackingList_{export.packing_list_number}_{pallet.pallet_number}.pdf"'
    )

    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response









# ---------- Barcode Helper ----------
def generate_barcode_base64(data, barcode_type="code128"):
    """Generate a barcode image and return base64 data URI."""
    BARCODE = barcode.get_barcode_class(barcode_type)
    my_barcode = BARCODE(data, writer=ImageWriter())
    buf = BytesIO()
    my_barcode.write(buf, options={"module_height": 15.0, "font_size": 10})
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

# ---------- SSCC Helper ----------
def calc_check_digit(number):
    """Calculate GS1 check digit (mod 10)."""
    total = 0
    reversed_digits = list(map(int, str(number)))[::-1]
    for idx, n in enumerate(reversed_digits, start=1):
        if idx % 2 == 0:
            total += n
        else:
            total += n * 3
    return (10 - (total % 10)) % 10

def generate_sscc(company_prefix, pallet_id):
    """
    Build SSCC:
      Extension (0) + CompanyPrefix + PalletID(serial) + CheckDigit
    """
    base = f"0{company_prefix}{str(pallet_id).zfill(9)}"
    check = calc_check_digit(base)
    return f"{base}{check}"

# ---------- View ----------
@login_required
def pallet_label_pdf_view(request, export_id, pallet_id):
    export = get_object_or_404(Export, id=export_id)
    pallet = get_object_or_404(Pallet, id=pallet_id, export=export)

    # Example GTIN (usually product-level code, here fixed)
    gtin_value = "00712345678905"

    # Auto-generate SSCC from company prefix + pallet_id
    company_prefix = "0789012"  # <-- replace with your real GS1 prefix!
    sscc_value = generate_sscc(company_prefix, pallet.id)

    # Generate barcodes
    gtin_barcode_uri = generate_barcode_base64(gtin_value)
    sscc_barcode_uri = generate_barcode_base64(sscc_value)

    unique_boxes_count = pallet.unique_boxes_count

    ctx = {
        "export": export,
        "pallet": pallet,
        "gtin_barcode_uri": gtin_barcode_uri,
        "sscc_barcode_uri": sscc_barcode_uri,
        "gtin_value": gtin_value,
        "sscc_value": sscc_value,
        "unique_boxes_count": unique_boxes_count,
    }


    html_string = render(request, "core/pallet_label.html", ctx).content.decode("utf-8")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="PalletLabel_{export.export_number}_P{pallet.pallet_number}.pdf"'
    )
    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(response)
    return response
