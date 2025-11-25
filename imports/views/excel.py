# imports/views/excel.py
import csv

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse

from ..models import Import, ImportLine
from ..permissions import has_imports_access


@login_required
@user_passes_test(has_imports_access)
def export_imports_excel(request):
    """
    Export imports (with same filters as dashboard) to CSV (Excel-friendly),
    including ALL important fields from the Import model.
    """
    q = (request.GET.get("q") or "").strip()
    status_f = (request.GET.get("status") or "").strip()
    method_f = (request.GET.get("method") or "").strip()

    qs = Import.objects.all()

    if q:
        qs = qs.filter(
            Q(import_code__icontains=q) |
            Q(vendor_name__icontains=q) |
            Q(tracking_no__icontains=q)
        )

    if status_f:
        qs = qs.filter(shipment_status=status_f)

    if method_f:
        qs = qs.filter(shipping_method=method_f)

    qs = qs.select_related("forwarder").order_by("-created_at")

    response = HttpResponse(content_type="text/csv")
    filename = "imports_export.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # 🔹 Header row – all fields you care about
    writer.writerow([
        "DB ID",
        "Import Code",
        "Vendor",
        "Exporter Country",
        "Incoterms",
        "Currency",
        "Goods Price",
        "Shipping Method",
        "Forwarder",
        "Shipment Status",
        "Vendor Reference",
        "Forwarder Reference",
        "Tracking Number",
        "Pickup Address",
        "Is Danger",
        "Is Stackable",
        "Notes",
        "Declaration C Number",
        "Declaration A Number",
        "Declaration Date",
        "Expected Receipt Date",
        "Total Gross Weight (kg)",
        "Total Volumetric Weight (kg)",
        "Created At",
    ])

    # 🔹 Data rows
    for imp in qs:
        writer.writerow([
            imp.pk,
            imp.import_code,
            imp.vendor_name or "",
            str(imp.exporter_country) if imp.exporter_country else "",
            imp.incoterms or "",
            imp.currency_code or "",
            str(imp.goods_price) if imp.goods_price is not None else "",
            imp.shipping_method or "",
            imp.forwarder.name if getattr(imp, "forwarder", None) else "",
            imp.shipment_status or "",
            imp.vendor_reference or "",
            imp.forwarder_reference or "",
            imp.tracking_no or "",
            (imp.pickup_address or "").replace("\r\n", " ").replace("\n", " "),
            "YES" if imp.is_danger else "NO",
            "YES" if imp.is_stackable else "NO",
            (imp.notes or "").replace("\r\n", " ").replace("\n", " "),
            imp.declaration_c_number or "",
            imp.declaration_a_number or "",
            imp.declaration_date.isoformat() if imp.declaration_date else "",
            imp.expected_receipt_date.isoformat() if imp.expected_receipt_date else "",
            str(imp.total_gross_weight_kg) if imp.total_gross_weight_kg is not None else "",
            str(imp.total_volumetric_weight_kg) if imp.total_volumetric_weight_kg is not None else "",
            imp.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    return response







# imports/views/exports.py (or wherever this view lives)

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill

from ..models import ImportLine
from ..permissions import has_imports_access


@login_required
@user_passes_test(has_imports_access)
def export_import_lines_excel(request):
    """
    Export all import lines to a styled Excel (.xlsx) file.
    """
    qs = (
        ImportLine.objects
        .select_related("import_header")
        .order_by("import_header__pk", "document_no", "line_no")
    )

    # Create workbook / sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Import Lines"

    # Header row (Tracking Number at the end)
    headers = [
        "Line ID",
        "Import ID",
        "Import Code",
        "Vendor",
        "Document No.",
        "Line No.",
        "Item No.",
        "Description",
        "Quantity",
        "Unit of Measure",
        "Unit Cost",
        "Line Amount",
        "Expected Receipt Date",
        "Delivery Date",
        "Tracking Number",
    ]
    ws.append(headers)

    # Header style: bold + light fill
    header_font = Font(bold=True)
    header_fill = PatternFill(fill_type="solid", fgColor="D9E1F2")  # light blue/gray

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    # Data rows
    for line in qs:
      imp = line.import_header
      ws.append([
          line.pk,
          imp.pk if imp else "",
          imp.import_code if imp else "",
          imp.vendor_name if imp else "",
          line.document_no or "",
          line.line_no or "",
          line.item_no or "",
          line.description or "",
          float(line.quantity) if line.quantity is not None else "",
          line.unit_of_measure or "",
          float(line.unit_cost) if line.unit_cost is not None else "",
          float(line.line_amount) if line.line_amount is not None else "",
          line.expected_receipt_date.isoformat() if line.expected_receipt_date else "",
          line.delivery_date.isoformat() if line.delivery_date else "",
          imp.tracking_no if imp and imp.tracking_no else "",
      ])

    # Auto-fit column widths
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        col_letter = get_column_letter(column_cells[0].column)
        ws.column_dimensions[col_letter].width = length + 2

    # Freeze top row
    ws.freeze_panes = "A2"

    # AutoFilter on header row
    last_col_letter = get_column_letter(ws.max_column)
    ws.auto_filter.ref = f"A1:{last_col_letter}{ws.max_row}"

    # Prepare HTTP response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="import_lines.xlsx"'

    wb.save(response)
    return response
