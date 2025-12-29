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


from decimal import Decimal, InvalidOperation
from datetime import datetime
import json

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..models import Import, ImportLine, ImportPackage
from ..permissions import has_imports_access


# imports/views/edit.py

import json
from decimal import Decimal, InvalidOperation
from datetime import datetime

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required  # , user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..models import Import, ImportLine, ImportPackage
# from ..permissions import has_imports_access


@login_required
# @user_passes_test(has_imports_access)
def edit_import(request, pk):
    imp = get_object_or_404(Import, pk=pk)
    vendors = Vendor.objects.all().order_by("name")
    forwarders = Forwarder.objects.all().order_by("name")

    # -------------------------
    # Helpers
    # -------------------------
    def _clean(val):
        if val is None:
            return None
        s = str(val).strip()
        return s or None

    def _dec_or_none(val):
        val = _clean(val)
        if not val:
            return None
        try:
            return Decimal(val.replace(",", ""))
        except (InvalidOperation, AttributeError):
            return None

    def _parse_date(key):
        v = _clean(request.POST.get(key))
        if not v:
            return None
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _build_packages_context(import_obj):
        packages_qs = ImportPackage.objects.filter(import_header=import_obj).order_by("pk")
        packages_list = []
        for p in packages_qs:
            packages_list.append({
                "type": p.package_type or "",
                "length": p.length_cm,          # already stored as cm
                "width": p.width_cm,
                "height": p.height_cm,
                "gross_weight": p.gross_weight_kg,  # already stored as kg
                "unit_system": "metric",        # ✅ we store metric in DB; UI toggle can still show imperial
            })
        return packages_list, json.dumps(packages_list, default=str)

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

    # -------------------------
    # Default view state (GET + fallback)
    # -------------------------
    packages_list, packages_json = _build_packages_context(imp)
    lines_data, lines_json = _build_lines_context(imp)

    if request.method == "POST":
        action = request.POST.get("action", "save")

        # =============================
        # EXCEL UPLOAD MODE (replace lines)
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
                    if not any(row):
                        continue

                    (
                        doc_no, line_no, item_no, desc, qty, uom, unit_cost,
                        line_amount, exp_rec_date, deliv_date, *_
                    ) = (list(row) + [None] * 10)[:10]

                    def _as_str(x):
                        return "" if x is None else str(x).strip()

                    def _as_dec(x):
                        try:
                            return Decimal(str(x).replace(",", "")) if x not in (None, "") else None
                        except (InvalidOperation, TypeError):
                            return None

                    def _as_date(x):
                        if isinstance(x, datetime):
                            return x.date()
                        if isinstance(x, str):
                            x = x.strip()
                            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                                try:
                                    return datetime.strptime(x, fmt).date()
                                except ValueError:
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

                if not new_lines:
                    messages.error(request, "Excel contains no valid data rows.")
                    return redirect("imports_edit", pk=imp.pk)

                imp.lines.all().delete()
                for l in new_lines:
                    ImportLine.objects.create(import_header=imp, **l)

                messages.success(request, f"{len(new_lines)} new lines uploaded and replaced successfully.")
            except Exception as e:
                messages.error(request, f"Excel error: {e}")

            return redirect("imports_edit", pk=imp.pk)

        # =============================
        # NORMAL SAVE MODE
        # =============================
        form = ExporterCountryForm(request.POST)
        if form.is_valid():
            data = request.POST

            def get_forwarder(key):
                fid = data.get(key)
                return Forwarder.objects.filter(pk=fid).first() if fid else None

            # forwarders
            imp.forwarder = get_forwarder("forwarder")
            imp.transport_forwarder = get_forwarder("transport_forwarder")
            imp.brokerage_forwarder = get_forwarder("brokerage_forwarder")
            imp.internal_delivery_forwarder = get_forwarder("internal_delivery_forwarder")
            imp.other1_forwarder = get_forwarder("other1_forwarder")
            imp.other2_forwarder = get_forwarder("other2_forwarder")

            # charges
            imp.transport_invoice_no = _clean(data.get("transport_invoice_no"))
            imp.transport_price = _dec_or_none(data.get("transport_price"))
            imp.transport_currency = _clean(data.get("transport_currency"))
            imp.transport_payment_date = _parse_date("transport_payment_date")

            imp.brokerage_invoice_no = _clean(data.get("brokerage_invoice_no"))
            imp.brokerage_price = _dec_or_none(data.get("brokerage_price"))
            imp.brokerage_currency = _clean(data.get("brokerage_currency"))
            imp.brokerage_payment_date = _parse_date("brokerage_payment_date")

            imp.internal_delivery_invoice_no = _clean(data.get("internal_delivery_invoice_no"))
            imp.internal_delivery_price = _dec_or_none(data.get("internal_delivery_price"))
            imp.internal_delivery_currency = _clean(data.get("internal_delivery_currency"))
            imp.internal_delivery_payment_date = _parse_date("internal_delivery_payment_date")

            imp.other1_invoice_no = _clean(data.get("other1_invoice_no"))
            imp.other1_price = _dec_or_none(data.get("other1_price"))
            imp.other1_currency = _clean(data.get("other1_currency"))
            imp.other1_payment_date = _parse_date("other1_payment_date")

            imp.other2_invoice_no = _clean(data.get("other2_invoice_no"))
            imp.other2_price = _dec_or_none(data.get("other2_price"))
            imp.other2_currency = _clean(data.get("other2_currency"))
            imp.other2_payment_date = _parse_date("other2_payment_date")

            # header
            imp.vendor_name = _clean(data.get("vendor_name")) or ""
            imp.exporter_country = form.cleaned_data.get("exporter_country")
            imp.incoterms = _clean(data.get("incoterms"))
            imp.currency_code = _clean(data.get("currency_code"))
            imp.goods_price = _dec_or_none(data.get("goods_price"))

            tracking = _clean(data.get("tracking_no"))
            imp.tracking_no = tracking.upper() if tracking else None

            imp.shipping_method = _clean(data.get("shipping_method"))
            imp.shipment_status = _clean(data.get("shipment_status"))
            imp.pickup_address = _clean(data.get("pickup_address"))
            imp.is_danger = bool(data.get("is_danger"))
            imp.is_stackable = bool(data.get("is_stackable"))
            imp.expected_receipt_date = _parse_date("expected_receipt_date")
            imp.notes = _clean(data.get("notes"))

            # customs
            imp.declaration_c_number = _clean(data.get("declaration_c_number"))
            imp.declaration_a_number = _clean(data.get("declaration_a_number"))
            imp.declaration_date = _parse_date("declaration_date")

            # -------------------------
            # PACKAGES replace + totals (✅ ALWAYS STORE CM/KG)
            # -------------------------
            ImportPackage.objects.filter(import_header=imp).delete()
            packages_raw = request.POST.get("packages_json")

            total_gw = Decimal("0")
            total_vol = Decimal("0")

            INCH_TO_CM = Decimal("2.54")
            LB_TO_KG = Decimal("0.45359237")
            VOL_DIVISOR = Decimal("6000")  # cm^3/kg

            def to_decimal_any(v):
                if v in (None, "", " "):
                    return None
                try:
                    return Decimal(str(v))
                except (InvalidOperation, TypeError):
                    return None

            if packages_raw:
                try:
                    packages = json.loads(packages_raw)
                except json.JSONDecodeError:
                    packages = []

                for p in packages:
                    p_type = (p.get("type") or "").upper() or None
                    unit_system = (p.get("unit_system") or "metric").lower()

                    length = to_decimal_any(p.get("length"))
                    width = to_decimal_any(p.get("width"))
                    height = to_decimal_any(p.get("height"))
                    gw = to_decimal_any(p.get("gross_weight"))

                    # Convert imperial -> metric before saving
                    if unit_system == "imperial":
                        if length is not None:
                            length = (length * INCH_TO_CM).quantize(Decimal("0.01"))
                        if width is not None:
                            width = (width * INCH_TO_CM).quantize(Decimal("0.01"))
                        if height is not None:
                            height = (height * INCH_TO_CM).quantize(Decimal("0.01"))
                        if gw is not None:
                            gw = (gw * LB_TO_KG).quantize(Decimal("0.001"))

                    # Skip empty rows
                    if not any([p_type, length, width, height, gw]):
                        continue

                    ImportPackage.objects.create(
                        import_header=imp,
                        package_type=p_type,
                        length_cm=length,
                        width_cm=width,
                        height_cm=height,
                        gross_weight_kg=gw,
                        unit_system="metric",  # ✅ DB always cm/kg
                    )

                    if gw is not None:
                        total_gw += gw
                    if length is not None and width is not None and height is not None:
                        total_vol += (length * width * height) / VOL_DIVISOR

            imp.total_gross_weight_kg = total_gw if total_gw != 0 else None
            imp.total_volumetric_weight_kg = total_vol.quantize(Decimal("0.001")) if total_vol != 0 else None

            imp.save()
            messages.success(request, f"Import {imp.import_code} updated successfully.")
            return redirect("imports_home")

        # if form invalid -> fall through to render with errors

    # -------------------------
    # GET render (or POST invalid form render)
    # -------------------------
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
@user_passes_test(has_imports_access)
def delete_import(request, pk):
    if not request.user.is_superuser:
        return redirect("imports_home")

    if request.method == "POST":
        imp = get_object_or_404(Import, pk=pk)
        imp.delete()
    return redirect("imports_home")
