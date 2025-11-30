# imports/views/excel.py
import csv

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse

from ..models import Import, ImportLine
from ..permissions import has_imports_access
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill

from ..models import ImportLine
from ..permissions import has_imports_access

# 🔴 TODO: adjust this import to your real Item model
# e.g. from admin_panel.models import Item
from admin_area.models import Item  
from openpyxl.styles import Font, PatternFill, Border, Side



from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill

from ..models import ImportLine
from ..permissions import has_imports_access
from admin_area.models import Item





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


# imports/views/excel.py
from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill

from ..models import ImportLine
from ..permissions import has_imports_access
from admin_area.models import Item  # ✅ use your existing Item model


# imports/views/excel.py
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill

from ..models import ImportLine
from ..permissions import has_imports_access
from admin_area.models import Item   # ✅ correct app name


@login_required
@user_passes_test(has_imports_access)
def export_import_lines_excel(request):
    """
    Export all import lines to a styled Excel (.xlsx) file,
    including:
      - header totals (GW / VW)
      - calculated line gross & volumetric weight
      - vendor/forwarder references & customs info
    """
    qs = (
        ImportLine.objects
        .select_related("import_header")
        .order_by("import_header__pk", "document_no", "line_no")
    )

    # ------------------------------------------------------------------
    # 1) Preload Items by item_no (ImportLine.item_no -> Item.number)
    # ------------------------------------------------------------------
    item_numbers = {line.item_no for line in qs if line.item_no}
    items = Item.objects.filter(number__in=item_numbers)
    item_map = {i.number: i for i in items}

    # ------------------------------------------------------------------
    # 2) Precompute total quantities per Import (for splitting totals)
    # ------------------------------------------------------------------
    total_qty_by_import = defaultdict(Decimal)
    for line in qs:
        if line.import_header_id and line.quantity is not None:
            total_qty_by_import[line.import_header_id] += line.quantity

    # ------------------------------------------------------------------
    # 3) Create workbook / sheet
    # ------------------------------------------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Import Lines"

    # Header row – reordered as you requested
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
        "Goods Currency",              # after Line Amount
        "Expected Receipt Date",
        "Delivery Date",
        "Created At",
        "Tracking Number",
        "Vendor Reference",            # all after Tracking Number
        "Forwarder Reference",
        "Declaration C Number",
        "Declaration A Number",
        "Declaration Date",
        "Incoterms",
        "Total Import GW (kg)",
        "Total Import VW (kg)",
        "Line Gross Weight (kg)",
        "Line Volumetric Weight (kg)",
    ]
    ws.append(headers)

    # Header style: bold + light fill + border
    header_font = Font(bold=True)
    header_fill = PatternFill(fill_type="solid", fgColor="D9E1F2")

    thin_border = Border(
        left=Side(border_style="thin", color="000000"),
        right=Side(border_style="thin", color="000000"),
        top=Side(border_style="thin", color="000000"),
        bottom=Side(border_style="thin", color="000000"),
    )

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    # ------------------------------------------------------------------
    # 4) Data rows with calculated line weights
    # ------------------------------------------------------------------
    for line in qs:
        imp = line.import_header
        qty = line.quantity or Decimal("0")

        total_gw_import = imp.total_gross_weight_kg if imp else None
        total_vw_import = imp.total_volumetric_weight_kg if imp else None
        total_qty = total_qty_by_import.get(imp.id if imp else None, Decimal("0"))

        # default = no weight
        line_gw = None
        line_vw = None

        # find matching item if exists
        item = item_map.get(line.item_no) if line.item_no else None

        if qty and imp:
            # ---- Gross weight per line ----
            if item and item.weight is not None:
                line_gw = item.weight * qty
            elif total_gw_import is not None and total_qty:
                line_gw = (total_gw_import * qty) / total_qty

            # ---- Volumetric weight per line ----
            if item and item.volumetric_weight is not None:
                line_vw = item.volumetric_weight * qty
            elif total_vw_import is not None and total_qty:
                line_vw = (total_vw_import * qty) / total_qty

        # append row
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
            imp.currency_code or "" if imp else "",                        # Goods Currency
            line.expected_receipt_date.isoformat() if line.expected_receipt_date else "",
            line.delivery_date.isoformat() if line.delivery_date else "",
            imp.created_at.strftime("%Y-%m-%d") if (imp and imp.created_at) else "",
            imp.tracking_no if (imp and imp.tracking_no) else "",
            imp.vendor_reference or "" if imp else "",
            imp.forwarder_reference or "" if imp else "",
            imp.declaration_c_number or "" if imp else "",
            imp.declaration_a_number or "" if imp else "",
            imp.declaration_date.isoformat() if (imp and imp.declaration_date) else "",
            imp.incoterms or "" if imp else "",
            float(total_gw_import) if total_gw_import is not None else "",
            float(total_vw_import) if total_vw_import is not None else "",
            float(line_gw) if line_gw is not None else "",
            float(line_vw) if line_vw is not None else "",
        ])

        # ----------------------------
        # Zebra stripe + borders
        # ----------------------------
        row_index = ws.max_row
        fill_color = "FFFFFF" if row_index % 2 == 0 else "F7F7F7"  # white / light gray

        for cell in ws[row_index]:
            cell.fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid",
            )
            cell.border = thin_border

    # ------------------------------------------------------------------
    # 5) Auto-fit column widths, freeze header, filter
    # ------------------------------------------------------------------
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        col_letter = get_column_letter(column_cells[0].column)
        ws.column_dimensions[col_letter].width = length + 2

    ws.freeze_panes = "A2"

    last_col_letter = get_column_letter(ws.max_column)
    ws.auto_filter.ref = f"A1:{last_col_letter}{ws.max_row}"

    # Prepare HTTP response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="import_lines.xlsx"'

    wb.save(response)
    return response
