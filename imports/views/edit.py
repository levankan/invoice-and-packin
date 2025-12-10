# imports/views/edit.py
from decimal import Decimal, InvalidOperation
from datetime import datetime
import json  # ✅ add this

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect

from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..models import Import, ImportPackage  # ✅ add ImportPackage
from ..permissions import has_imports_access
from django.contrib import messages
import openpyxl 
# imports/views/edit.py
from decimal import Decimal, InvalidOperation
from datetime import datetime
import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect

from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..models import Import, ImportPackage
from ..permissions import has_imports_access

import json
from decimal import Decimal
from datetime import datetime

import openpyxl
from django.contrib import messages

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test

from ..models import Import, ImportLine, ImportPackage
from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..permissions import has_imports_access


@login_required
@user_passes_test(has_imports_access)
def edit_import(request, pk):
    imp = get_object_or_404(Import, pk=pk)
    vendors = Vendor.objects.all().order_by("name")
    forwarders = Forwarder.objects.all().order_by("name")

    def _clean(val):
        if val is None:
            return None
        s = str(val).strip()
        return s or None

    def _parse_date(key):
        v = _clean(request.POST.get(key))
        if not v:
            return None
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            return None

    # =============================
    # ✅ LOAD PACKAGES FROM DB
    # =============================
    def _build_packages_context(import_obj):
        packages_qs = ImportPackage.objects.filter(import_header=import_obj).order_by("pk")
        packages_list = []
        for p in packages_qs:
            packages_list.append({
                "type": p.package_type or "",
                "length": p.length_cm,
                "width": p.width_cm,
                "height": p.height_cm,
                "gross_weight": p.gross_weight_kg,
                "unit_system": p.unit_system or "metric",
            })
        return packages_list, json.dumps(packages_list, default=str)

    # =============================
    # ✅ LOAD LINES FROM DB
    # =============================
    def _build_lines_context(import_obj):
        lines_qs = import_obj.lines.all().order_by("pk")
        lines_list = []
        for l in lines_qs:
            lines_list.append({
                "document_no": l.document_no or "",
                "line_no": l.line_no or "",
                "item_no": l.item_no or "",
                "description": l.description or "",
                "quantity": l.quantity,
                "unit_of_measure": l.unit_of_measure or "",
                "unit_cost": l.unit_cost,
                "line_amount": l.line_amount,
                "expected_receipt_date": l.expected_receipt_date.isoformat() if l.expected_receipt_date else "",
                "delivery_date": l.delivery_date.isoformat() if l.delivery_date else "",
            })
        return lines_list, json.dumps(lines_list, default=str)

    # ✅ DEFAULT VIEW STATE (GET)
    packages_list, packages_json = _build_packages_context(imp)
    lines_data, lines_json = _build_lines_context(imp)

    # ============================================================
    # ✅ POST
    # ============================================================
    if request.method == "POST":
        action = request.POST.get("action", "save")

        # =============================
        # ✅ EXCEL UPLOAD MODE
        # =============================
        if action == "upload_lines":
            upload = request.FILES.get("lines_file")

            if not upload:
                messages.error(request, "Please choose an Excel file.")
                return redirect("imports_edit", pk=imp.pk)

            try:
                wb = openpyxl.load_workbook(upload, data_only=True)
                sheet = wb.active

                new_lines = []

                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not any(row):   # ✅ SAFE CHECK (same as register page)
                        continue

                    (
                        doc_no,
                        line_no,
                        item_no,
                        desc,
                        qty,
                        uom,
                        unit_cost,
                        line_amount,
                        exp_rec_date,
                        deliv_date,
                        *_,
                    ) = (list(row) + [None] * 10)[:10]

                    def _as_str(x):
                        return "" if x is None else str(x).strip()

                    def _as_dec(x):
                        try:
                            return Decimal(str(x)) if x not in (None, "") else None
                        except:
                            return None

                    def _as_date(x):
                        if isinstance(x, datetime):
                            return x.date()
                        if isinstance(x, str):
                            x = x.strip()
                            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                                try:
                                    return datetime.strptime(x, fmt).date()
                                except:
                                    continue
                        return None

                    new_lines.append({
                        "document_no": _as_str(doc_no),
                        "line_no": _as_str(line_no),
                        "item_no": _as_str(item_no),
                        "description": _as_str(desc),
                        "quantity": _as_dec(qty),
                        "unit_of_measure": _as_str(uom),
                        "unit_cost": _as_dec(unit_cost),
                        "line_amount": _as_dec(line_amount),
                        "expected_receipt_date": _as_date(exp_rec_date),
                        "delivery_date": _as_date(deliv_date),
                    })

                # ✅ ONLY NOW delete + insert
                if not new_lines:
                    messages.error(request, "Excel contains no valid data rows.")
                    return redirect("imports_edit", pk=imp.pk)

                imp.lines.all().delete()

                for l in new_lines:
                    ImportLine.objects.create(
                        import_header=imp,
                        **l
                    )

                messages.success(
                    request, f"{len(new_lines)} new lines uploaded and replaced successfully."
                )

            except Exception as e:
                messages.error(request, f"Excel error: {e}")

            return redirect("imports_edit", pk=imp.pk)


        # =============================
        # ✅ NORMAL SAVE MODE
        # =============================
        form = ExporterCountryForm(request.POST)
        if form.is_valid():
            data = request.POST

            def get_forwarder(key):
                fid = data.get(key)
                return Forwarder.objects.filter(pk=fid).first() if fid else None

            imp.forwarder = get_forwarder("forwarder")
            imp.transport_forwarder = get_forwarder("transport_forwarder")
            imp.brokerage_forwarder = get_forwarder("brokerage_forwarder")
            imp.internal_delivery_forwarder = get_forwarder("internal_delivery_forwarder")
            imp.other1_forwarder = get_forwarder("other1_forwarder")
            imp.other2_forwarder = get_forwarder("other2_forwarder")

            imp.vendor_name = _clean(data.get("vendor_name")) or ""
            imp.exporter_country = form.cleaned_data.get("exporter_country")
            imp.incoterms = _clean(data.get("incoterms"))
            imp.currency_code = _clean(data.get("currency_code"))
            imp.goods_price = Decimal(data.get("goods_price")) if data.get("goods_price") else None
            imp.tracking_no = _clean(data.get("tracking_no"))
            imp.shipping_method = _clean(data.get("shipping_method"))
            imp.shipment_status = _clean(data.get("shipment_status"))
            imp.pickup_address = _clean(data.get("pickup_address"))
            imp.is_danger = bool(data.get("is_danger"))
            imp.is_stackable = bool(data.get("is_stackable"))
            imp.expected_receipt_date = _parse_date("expected_receipt_date")
            imp.notes = _clean(data.get("notes"))
            # ✅ SAVE CUSTOMS DECLARATION
            imp.declaration_c_number = _clean(data.get("declaration_c_number"))
            imp.declaration_a_number = _clean(data.get("declaration_a_number"))
            imp.declaration_date = _parse_date("declaration_date")
            # =============================
            # ✅ UPDATE PACKAGES FROM EDIT PAGE
            # =============================
            ImportPackage.objects.filter(import_header=imp).delete()

            packages_raw = request.POST.get("packages_json")

            total_gw = Decimal("0")
            total_vol = Decimal("0")

            if packages_raw:
                try:
                    packages = json.loads(packages_raw)
                except json.JSONDecodeError:
                    packages = []

                for p in packages:
                    length = Decimal(p.get("length")) if p.get("length") else None
                    width = Decimal(p.get("width")) if p.get("width") else None
                    height = Decimal(p.get("height")) if p.get("height") else None
                    gw = Decimal(p.get("gross_weight")) if p.get("gross_weight") else None

                    ImportPackage.objects.create(
                        import_header=imp,
                        package_type=p.get("type"),
                        length_cm=length,
                        width_cm=width,
                        height_cm=height,
                        gross_weight_kg=gw,
                        unit_system=p.get("unit_system", "metric"),
                    )

                    if gw:
                        total_gw += gw

                    if length and width and height:
                        total_vol += (length * width * height) / Decimal("6000")

            # ✅ SAVE TOTALS
            imp.total_gross_weight_kg = total_gw if total_gw != 0 else None
            imp.total_volumetric_weight_kg = total_vol if total_vol != 0 else None


            imp.save()
            return redirect("imports_home")

    # ============================================================
    # ✅ FINAL GET RENDER
    # ============================================================
    form = ExporterCountryForm(initial={"exporter_country": imp.exporter_country})
    return render(
        request,
        "imports/register_imports.html",
        {
            "vendors": vendors,
            "forwarders": forwarders,
            "form": form,
            "import_obj": imp,
            "lines_data": lines_data,
            "lines_json": lines_json,
            "packages_json": packages_json,
            "packages_list": packages_list,
        },
    )






@login_required
def delete_import(request, pk):
    if not request.user.is_superuser:
        return redirect("imports_home")

    if request.method == "POST":
        imp = get_object_or_404(Import, pk=pk)
        imp.delete()
    return redirect("imports_home")
