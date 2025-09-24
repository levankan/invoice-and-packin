from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from core.models import Export
from core.forms import ExportForm
import openpyxl
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from core.models import Export, LineItem






@login_required
def exports_view(request):
    """List and search exports"""
    q = request.GET.get("q", "")
    exports = Export.objects.all().order_by("-created_at")
    if q:
        exports = exports.filter(
            Q(invoice_number__icontains=q) |
            Q(project_no__icontains=q) |
            Q(export_number__icontains=q)
        )
    return render(request, "core/exports.html", {"exports": exports})


@login_required
def edit_export(request, export_id):
    """Edit a single export"""
    export = get_object_or_404(Export, id=export_id)
    if request.method == "POST":
        form = ExportForm(request.POST, instance=export)
        if form.is_valid():
            form.save()
            messages.success(request, "Export updated successfully ✅")
            return redirect("exports_view")
    else:
        form = ExportForm(instance=export)
    return render(request, "core/edit_export.html", {"form": form, "export": export})


@login_required
def delete_export(request, export_id):
    # ✅ Only superuser (admin) can delete
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to delete exports.")

    export = get_object_or_404(Export, id=export_id)

    if request.method == "POST":
        export.delete()
        return redirect("exports_view")

    return render(request, "core/delete_export.html", {"export": export})






@login_required
def download_export_template(request):
    # Create workbook
    wb = openpyxl.Workbook()

    # =====================
    # Sheet 1: Export Items
    # =====================
    ws1 = wb.active
    ws1.title = "Sheet1"

    headers_items = [
        "Serial/Lot Number", "Document Number", "Item Number",
        "Cross Reference #", "QTY", "Unit of Measure", "Box #",
        "Commercial Invoice #", "Posting Date", "Shipment #",
        "Description", "Carbon QTY", "Carbon LOT", "Customer PO",
        "PO Line", "Sales Order", "Sales Order Line", "Pallet #",
        "Price", "LU"
    ]

    for col_num, header in enumerate(headers_items, 1):
        ws1.cell(row=1, column=col_num, value=header)

    # =====================
    # Sheet 2: Pallets
    # =====================
    ws2 = wb.create_sheet(title="Sheet2")

    headers_pallets = [
        "Pallet #", "Lenght (Cm)", "Width (Cm)", "Height (Cm)", "Gross Weight (Kg)"
    ]

    for col_num, header in enumerate(headers_pallets, 1):
        ws2.cell(row=1, column=col_num, value=header)

    # =====================
    # Response
    # =====================
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Export_Template.xlsx"'

    wb.save(response)
    return response







@login_required
def export_database_excel(request):
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exports Full"

    # Headers in your requested order
    headers = [
        "Serial/Lot Number", "Document Number", "Item Number", "Cross Reference #",
        "QTY", "Unit of Measure", "Box #", "Commercial Invoice #", "Posting Date",
        "Shipment #", "Description", "Carbon QTY", "Carbon LOT", "Customer PO",
        "PO Line", "Sales Order", "Sales Order Line", "Pallet #", "Price", "LU",
        "Invoice No", "Packing List No", "Export No", "Project No", "Created At",
        "Seller", "Sold To", "Shipped To", "Export ID"
    ]
    ws.append(headers)

    # Data rows
    for exp in Export.objects.all().prefetch_related("items").order_by("id"):
        for item in exp.items.all():
            ws.append([
                item.serial_lot_number or "",
                item.document_number or "",
                item.item_number or "",
                item.cross_reference or "",
                item.qty or 0,
                item.unit_of_measure or "",
                item.box_number or "",
                item.commercial_invoice_number or "",
                item.posting_date.strftime("%Y-%m-%d") if item.posting_date else "",
                item.shipment_number or "",
                item.description or "",
                item.carbon_qty or "",
                item.carbon_lot or "",
                item.customer_po or "",
                item.po_line or "",
                item.sales_order or "",
                item.sales_order_line or "",
                item.pallet_number or "",
                item.price or 0,
                item.lu or "",
                exp.invoice_number or "",
                exp.packing_list_number or "",   # ✅ added packing list number
                exp.export_number or "",
                exp.project_no or "",
                exp.created_at.strftime("%Y-%m-%d"),
                exp.seller or "",
                exp.sold_to or "",
                exp.shipped_to or "",
                exp.id,
            ])

    # Response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Exports_Database.xlsx"'
    wb.save(response)
    return response
