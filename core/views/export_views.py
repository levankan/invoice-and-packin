from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from core.models import Export
from core.forms import ExportForm
import openpyxl
from django.http import HttpResponse




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
    export = get_object_or_404(Export, id=export_id)
    export.delete()
    messages.success(request, "Export deleted successfully 🗑")
    return redirect("exports_view")







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
