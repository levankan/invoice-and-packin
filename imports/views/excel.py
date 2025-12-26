# imports/views/excel.py
import csv

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ..models import Import, ImportLine, ImportPackage
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

from openpyxl import Workbook
from datetime import date



from django.db.models import Q
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Border, Side
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from ..models import Import
from ..permissions import has_imports_access
from decimal import Decimal


@login_required
@user_passes_test(has_imports_access)
def export_imports_excel(request):
    """
    Export imports (with same filters as dashboard) to a styled Excel (.xlsx),
    including all important fields from the Import model.
    """
    q = (request.GET.get("q") or "").strip()
    # support multi-select filters, same as dashboard
    status_f = request.GET.getlist("status")    # list
    method_f = request.GET.getlist("method")    # list

    qs = (
        Import.objects
        .select_related("forwarder")
        .order_by("-created_at")
    )

    if q:
        qs = qs.filter(
            Q(import_code__icontains=q)
            | Q(vendor_name__icontains=q)
            | Q(tracking_no__icontains=q)
            | Q(vendor_reference__icontains=q)
            | Q(forwarder_reference__icontains=q)
            | Q(lines__item_no__icontains=q)
            | Q(lines__document_no__icontains=q)
        ).distinct()

    if status_f:
        qs = qs.filter(shipment_status__in=status_f)

    if method_f:
        qs = qs.filter(shipping_method__in=method_f)

    # ------------------------------
    # 1) Create workbook / sheet
    # ------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Imports"

    headers = [
        "DB ID",
        "Import Code",
        "Vendor",
        "Exporter Country",
        "Incoterms",
        "Currency",
        "Goods Price",
        "Shipping Method",
        "Shipment Status",
        "Forwarder",
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
        "ATC Receipt Date",
        "Created At",

        "Transport Forwarder",
        "Transportation Invoice No",
        "Transportation Price",
        "Transportation Currency",
        "Transportation Payment Date",

        "Brokerage Forwarder",
        "Brokerage Invoice No",
        "Brokerage Price",
        "Brokerage Currency",
        "Brokerage Payment Date",

        "Internal Delivery Forwarder",
        "Internal Delivery Invoice No",
        "Internal Delivery Price",
        "Internal Delivery Currency",
        "Internal Delivery Payment Date",

        "Other1 Forwarder",
        "Other Charge #1 Invoice No",
        "Other Charge #1 Price",
        "Other Charge #1 Currency",
        "Other Charge #1 Payment Date",

        "Other2 Forwarder",
        "Other Charge #2 Invoice No",
        "Other Charge #2 Price",
        "Other Charge #2 Currency",
        "Other Charge #2 Payment Date",

        "Total Gross Weight (kg)",
        "Total Volumetric Weight (kg)",
        
    ]
    ws.append(headers)

    # styles
    header_font = Font(bold=True)
    header_fill = PatternFill(fill_type="solid", fgColor="D9E1F2")
    thin_border = Border(
        left=Side(border_style="thin", color="000000"),
        right=Side(border_style="thin", color="000000"),
        top=Side(border_style="thin", color="000000"),
        bottom=Side(border_style="thin", color="000000"),
    )

    # style header row
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    # ------------------------------
    # 2) Data rows
    # ------------------------------
    for imp in qs:
        row = [
            imp.pk,
            imp.import_code,
            imp.vendor_name or "",
            str(imp.exporter_country) if imp.exporter_country else "",
            imp.incoterms or "",
            imp.currency_code or "",
            float(imp.goods_price) if imp.goods_price is not None else "",
            imp.shipping_method or "",
            imp.shipment_status or "",
            imp.forwarder.name if getattr(imp, "forwarder", None) else "",
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
            imp.created_at.strftime("%Y-%m-%d %H:%M") if imp.created_at else "",

            imp.transport_forwarder.name if imp.transport_forwarder else "",
            imp.transport_invoice_no or "",
            float(imp.transport_price) if imp.transport_price is not None else "",
            imp.transport_currency or "",
            imp.transport_payment_date.isoformat() if imp.transport_payment_date else "",

            imp.brokerage_forwarder.name if imp.brokerage_forwarder else "",
            imp.brokerage_invoice_no or "",
            float(imp.brokerage_price) if imp.brokerage_price is not None else "",
            imp.brokerage_currency or "",
            imp.brokerage_payment_date.isoformat() if imp.brokerage_payment_date else "",

            imp.internal_delivery_forwarder.name if imp.internal_delivery_forwarder else "",
            imp.internal_delivery_invoice_no or "",
            float(imp.internal_delivery_price) if imp.internal_delivery_price is not None else "",
            imp.internal_delivery_currency or "",
            imp.internal_delivery_payment_date.isoformat() if imp.internal_delivery_payment_date else "",

            imp.other1_forwarder.name if imp.other1_forwarder else "",
            imp.other1_invoice_no or "",
            float(imp.other1_price) if imp.other1_price is not None else "",
            imp.other1_currency or "",
            imp.other1_payment_date.isoformat() if imp.other1_payment_date else "",

            imp.other2_forwarder.name if imp.other2_forwarder else "",
            imp.other2_invoice_no or "",
            float(imp.other2_price) if imp.other2_price is not None else "",
            imp.other2_currency or "",
            imp.other2_payment_date.isoformat() if imp.other2_payment_date else "",


            float(imp.total_gross_weight_kg) if imp.total_gross_weight_kg is not None else "",
            float(imp.total_volumetric_weight_kg) if imp.total_volumetric_weight_kg is not None else "",
            
        ]
        ws.append(row)

        row_idx = ws.max_row
        # zebra striping
        fill_color = "FFFFFF" if row_idx % 2 == 0 else "F7F7F7"
        for cell in ws[row_idx]:
            cell.fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid",
            )
            cell.border = thin_border

    # ------------------------------
    # 3) Auto-fit, freeze, filter
    # ------------------------------
    for column_cells in ws.columns:
        length = max(len(str(c.value)) if c.value else 0 for c in column_cells)
        col_letter = get_column_letter(column_cells[0].column)
        ws.column_dimensions[col_letter].width = length + 2

    ws.freeze_panes = "A2"
    last_col = get_column_letter(ws.max_column)
    ws.auto_filter.ref = f"A1:{last_col}{ws.max_row}"

    # ------------------------------
    # 4) Response
    # ------------------------------
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="imports_export.xlsx"'
    wb.save(response)
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


from collections import defaultdict
from decimal import Decimal
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

@login_required
@user_passes_test(has_imports_access)
def export_import_lines_excel(request):
    """
    Export all import lines to a styled Excel (.xlsx) file,
    including:
      - header totals (GW / VW)
      - calculated line gross & volumetric weight
      - vendor/forwarder references & customs info
      - Vendor VRS = (Register Date - Delivery Date) in days
    """
    qs = (
        ImportLine.objects
        .select_related("import_header")
        .order_by(
            "-import_header__created_at",  # newest imports first ✅
            "document_no",
            "line_no",
        )
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
        "Goods Currency",
        "Expected Receipt Date",
        "Delivery Date",
        "ATC Receipt Date",
        "Created At",
        "Shipment Status",
        "Tracking Number",
        "Vendor Reference",
        "Forwarder Reference",
        "Declaration C Number",
        "Declaration A Number",
        "Declaration Date",
        "Incoterms",
        "Total Import GW (kg)",
        "Total Import VW (kg)",
        "Line Gross Weight (kg)",
        "Line Volumetric Weight (kg)",
        "Vendor VRS",  # ✅ NEW COLUMN
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
    # 4) Data rows with calculated line weights + Vendor VRS
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

        # ✅ Vendor VRS = Register Date (imp.created_at) - Delivery Date (line.delivery_date)
        vendor_vrs = ""
        register_date = imp.created_at if imp else None
        delivery_date = line.delivery_date
        if register_date and delivery_date:
            vendor_vrs = (register_date.date() - delivery_date).days

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
            (imp.currency_code or "") if imp else "",
            line.expected_receipt_date.isoformat() if line.expected_receipt_date else "",
            line.delivery_date.isoformat() if line.delivery_date else "",
            imp.expected_receipt_date.isoformat() if (imp and imp.expected_receipt_date) else "",
            imp.created_at.strftime("%Y-%m-%d") if (imp and imp.created_at) else "",
            (imp.shipment_status or "") if imp else "",
            imp.tracking_no if (imp and imp.tracking_no) else "",
            (imp.vendor_reference or "") if imp else "",
            (imp.forwarder_reference or "") if imp else "",
            (imp.declaration_c_number or "") if imp else "",
            (imp.declaration_a_number or "") if imp else "",
            imp.declaration_date.isoformat() if (imp and imp.declaration_date) else "",
            (imp.incoterms or "") if imp else "",
            float(total_gw_import) if total_gw_import is not None else "",
            float(total_vw_import) if total_vw_import is not None else "",
            float(line_gw) if line_gw is not None else "",
            float(line_vw) if line_vw is not None else "",
            vendor_vrs,  # ✅ IMPORTANT: add the value at the end
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





@login_required
@user_passes_test(has_imports_access)
def export_single_import_excel(request, import_id):
    """
    Export a single import into an Excel file:

    Sheet1: header info + all lines for that import (same structure as
            export_imports_excel + export_import_lines_excel combined).
    Sheet2: all packages (dimensions) for this import.
    """
    # --------------------------
    # Fetch import + its lines
    # --------------------------
    imp = get_object_or_404(
        Import.objects.select_related("forwarder").prefetch_related("lines"),
        pk=import_id,
    )
    lines = imp.lines.all().order_by("document_no", "line_no")

    # --------------------------
    # Create workbook / sheet 1
    # --------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = f"Import {imp.import_code}"

    thin_border = Border(
        left=Side(border_style="thin", color="000000"),
        right=Side(border_style="thin", color="000000"),
        top=Side(border_style="thin", color="000000"),
        bottom=Side(border_style="thin", color="000000"),
    )

    header_font = Font(bold=True)
    header_fill = PatternFill(fill_type="solid", fgColor="D9E1F2")

    # --------------------------
    # PART 1: header from export_imports_excel
    # --------------------------
    header_row_1 = [
        "Import ID",
        "Import Code",
        "Vendor",
        "Exporter Country",
        "Incoterms",
        "Currency",
        "Goods Price",
        "Shipping Method",
        "Shipment Status",
        "Tracking Number",
        "Vendor Reference",
        "Forwarder Reference",
        "Declaration C Number",
        "Declaration A Number",
        "Declaration Date",
        "Expected Receipt Date",
        "Pickup Address",
        "Is Dangerous",
        "Is Stackable",
        "Total Gross Weight (kg)",
        "Total Volumetric Weight (kg)",
        "Forwarder",
        "Created At",
    ]
    ws.append(header_row_1)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    row2 = [
        imp.pk,
        imp.import_code,
        imp.vendor_name,
        str(imp.exporter_country) if imp.exporter_country else "",
        imp.incoterms or "",
        imp.currency_code or "",
        float(imp.goods_price) if imp.goods_price is not None else "",
        imp.shipping_method or "",
        imp.shipment_status or "",
        imp.tracking_no or "",
        imp.vendor_reference or "",
        imp.forwarder_reference or "",
        imp.declaration_c_number or "",
        imp.declaration_a_number or "",
        imp.declaration_date.isoformat() if imp.declaration_date else "",
        imp.expected_receipt_date.isoformat() if imp.expected_receipt_date else "",
        imp.pickup_address or "",
        "Yes" if imp.is_danger else "No",
        "Yes" if imp.is_stackable else "No",
        float(imp.total_gross_weight_kg) if imp.total_gross_weight_kg is not None else "",
        float(imp.total_volumetric_weight_kg) if imp.total_volumetric_weight_kg is not None else "",
        imp.forwarder.name if imp.forwarder else "",
        imp.created_at.strftime("%Y-%m-%d") if imp.created_at else "",
    ]
    ws.append(row2)
    for cell in ws[2]:
        cell.border = thin_border

    # blank row
    ws.append([])

    # --------------------------
    # PART 2: lines from export_import_lines_excel (for this import)
    # --------------------------
    # same headers as that function (plus ATC receipt date)
    line_headers = [
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
        "Goods Currency",
        "Expected Receipt Date",
        "Delivery Date",
        "ATC Receipt Date",
        "Created At",
        "Shipment Status", 
        "Tracking Number",
        "Vendor Reference",
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
    start_row_lines = ws.max_row + 1
    ws.append(line_headers)
    for cell in ws[start_row_lines]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    # For weights: we can reuse the logic from export_import_lines_excel,
    # but here only for this single import.
    from admin_area.models import Item  # if not already imported globally
    item_numbers = {l.item_no for l in lines if l.item_no}
    items = Item.objects.filter(number__in=item_numbers)
    item_map = {i.number: i for i in items}

    total_qty = Decimal("0")
    for l in lines:
        if l.quantity is not None:
            total_qty += l.quantity

    total_gw_import = imp.total_gross_weight_kg or Decimal("0")
    total_vw_import = imp.total_volumetric_weight_kg or Decimal("0")

    for l in lines:
        qty = l.quantity or Decimal("0")
        line_gw = None
        line_vw = None
        item = item_map.get(l.item_no) if l.item_no else None

        if qty:
            # gross weight
            if item and item.weight is not None:
                line_gw = item.weight * qty
            elif total_gw_import and total_qty:
                line_gw = (total_gw_import * qty) / total_qty

            # volumetric weight
            if item and item.volumetric_weight is not None:
                line_vw = item.volumetric_weight * qty
            elif total_vw_import and total_qty:
                line_vw = (total_vw_import * qty) / total_qty

        ws.append([
            l.pk,
            imp.pk,
            imp.import_code,
            imp.vendor_name,
            l.document_no or "",
            l.line_no or "",
            l.item_no or "",
            l.description or "",
            float(l.quantity) if l.quantity is not None else "",
            l.unit_of_measure or "",
            float(l.unit_cost) if l.unit_cost is not None else "",
            float(l.line_amount) if l.line_amount is not None else "",
            imp.currency_code or "",
            l.expected_receipt_date.isoformat() if l.expected_receipt_date else "",
            l.delivery_date.isoformat() if l.delivery_date else "",
            imp.expected_receipt_date.isoformat() if imp.expected_receipt_date else "",
            imp.created_at.strftime("%Y-%m-%d") if imp.created_at else "",
            imp.shipment_status or "",  
            imp.tracking_no or "",
            imp.vendor_reference or "",
            imp.forwarder_reference or "",
            imp.declaration_c_number or "",
            imp.declaration_a_number or "",
            imp.declaration_date.isoformat() if imp.declaration_date else "",
            imp.incoterms or "",
            float(total_gw_import) if total_gw_import else "",
            float(total_vw_import) if total_vw_import else "",
            float(line_gw) if line_gw is not None else "",
            float(line_vw) if line_vw is not None else "",
        ])

        # style row
        row_idx = ws.max_row
        fill_color = "FFFFFF" if row_idx % 2 == 0 else "F7F7F7"
        for cell in ws[row_idx]:
            cell.fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid",
            )
            cell.border = thin_border

    # autofit columns in sheet 1
    for column_cells in ws.columns:
        length = max(len(str(c.value)) if c.value else 0 for c in column_cells)
        col_letter = get_column_letter(column_cells[0].column)
        ws.column_dimensions[col_letter].width = length + 2

    ws.freeze_panes = "A2"

    # ==========================================================
    # SHEET 2: PACKAGES (dimensions for this import)
    # ==========================================================
    ws2 = wb.create_sheet(title="Packages", index=1)

    pkg_headers = [
        "Package ID",
        "Import ID",
        "Import Code",
        "Package Type",
        "Length (cm)",
        "Width (cm)",
        "Height (cm)",
        "Gross Weight (kg)",
        "Unit System",
    ]
    ws2.append(pkg_headers)
    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    packages = ImportPackage.objects.filter(import_header=imp).order_by("pk")

    for pkg in packages:
        ws2.append([
            pkg.pk,
            imp.pk,
            imp.import_code,
            pkg.package_type or "",
            float(pkg.length_cm) if pkg.length_cm is not None else "",
            float(pkg.width_cm) if pkg.width_cm is not None else "",
            float(pkg.height_cm) if pkg.height_cm is not None else "",
            float(pkg.gross_weight_kg) if pkg.gross_weight_kg is not None else "",
            pkg.unit_system or "",
        ])

        row_idx = ws2.max_row
        fill_color = "FFFFFF" if row_idx % 2 == 0 else "F7F7F7"
        for cell in ws2[row_idx]:
            cell.fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid",
            )
            cell.border = thin_border

    # autofit columns in sheet 2
    for column_cells in ws2.columns:
        length = max(len(str(c.value)) if c.value else 0 for c in column_cells)
        col_letter = get_column_letter(column_cells[0].column)
        ws2.column_dimensions[col_letter].width = length + 2

    ws2.freeze_panes = "A2"

    # --------------------------
    # Return response
    # --------------------------
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"import_{imp.import_code}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response
