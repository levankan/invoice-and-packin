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

    if request.method == "POST":
        form = ExporterCountryForm(request.POST)
        if form.is_valid():
            data = request.POST

            # ✅✅✅ SAFE FORWARDER RESOLUTION
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

            gp = _clean(data.get("goods_price"))
            imp.goods_price = Decimal(gp) if gp else None

            tracking = _clean(data.get("tracking_no"))
            imp.tracking_no = tracking.upper() if tracking else None

            imp.shipping_method = _clean(data.get("shipping_method"))
            imp.shipment_status = _clean(data.get("shipment_status"))
            imp.pickup_address = _clean(data.get("pickup_address"))
            imp.is_danger = bool(data.get("is_danger"))
            imp.is_stackable = bool(data.get("is_stackable"))
            imp.expected_receipt_date = _parse_date("expected_receipt_date")
            imp.notes = _clean(data.get("notes"))
            imp.vendor_reference = _clean(data.get("vendor_reference"))
            imp.forwarder_reference = _clean(data.get("forwarder_reference"))

            imp.declaration_c_number = _clean(data.get("declaration_c_number"))
            imp.declaration_a_number = _clean(data.get("declaration_a_number"))
            imp.declaration_date = _parse_date("declaration_date")

            # ✅ TRANSPORT
            imp.transport_invoice_no = _clean(data.get("transport_invoice_no"))
            imp.transport_price = Decimal(data.get("transport_price")) if data.get("transport_price") else None
            imp.transport_currency = _clean(data.get("transport_currency"))
            imp.transport_payment_date = _parse_date("transport_payment_date")

            # ✅ BROKERAGE
            imp.brokerage_invoice_no = _clean(data.get("brokerage_invoice_no"))
            imp.brokerage_price = Decimal(data.get("brokerage_price")) if data.get("brokerage_price") else None
            imp.brokerage_currency = _clean(data.get("brokerage_currency"))
            imp.brokerage_payment_date = _parse_date("brokerage_payment_date")

            # ✅ INTERNAL DELIVERY
            imp.internal_delivery_invoice_no = _clean(data.get("internal_delivery_invoice_no"))
            imp.internal_delivery_price = Decimal(data.get("internal_delivery_price")) if data.get("internal_delivery_price") else None
            imp.internal_delivery_currency = _clean(data.get("internal_delivery_currency"))
            imp.internal_delivery_payment_date = _parse_date("internal_delivery_payment_date")

            # ✅ OTHER #1
            imp.other1_invoice_no = _clean(data.get("other1_invoice_no"))
            imp.other1_price = Decimal(data.get("other1_price")) if data.get("other1_price") else None
            imp.other1_currency = _clean(data.get("other1_currency"))
            imp.other1_payment_date = _parse_date("other1_payment_date")

            # ✅ OTHER #2
            imp.other2_invoice_no = _clean(data.get("other2_invoice_no"))
            imp.other2_price = Decimal(data.get("other2_price")) if data.get("other2_price") else None
            imp.other2_currency = _clean(data.get("other2_currency"))
            imp.other2_payment_date = _parse_date("other2_payment_date")

            # ✅ PACKAGE UPDATE
            ImportPackage.objects.filter(import_header=imp).delete()
            packages_raw = data.get("packages_json")

            total_gw = Decimal("0")
            total_vol = Decimal("0")

            if packages_raw:
                packages = json.loads(packages_raw)
                for p in packages:
                    length = Decimal(p.get("length")) if p.get("length") else None
                    width = Decimal(p.get("width")) if p.get("width") else None
                    height = Decimal(p.get("height")) if p.get("height") else None
                    gw = Decimal(p.get("gross_weight")) if p.get("gross_weight") else None

                    pkg = ImportPackage.objects.create(
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

            imp.total_gross_weight_kg = total_gw if total_gw != 0 else None
            imp.total_volumetric_weight_kg = total_vol if total_vol != 0 else None

            imp.save()
            return redirect("imports_home")

        else:
            packages_list, packages_json = _build_packages_context(imp)
    else:
        form = ExporterCountryForm(initial={"exporter_country": imp.exporter_country})
        packages_list, packages_json = _build_packages_context(imp)

    return render(
        request,
        "imports/register_imports.html",
        {
            "vendors": vendors,
            "forwarders": forwarders,
            "form": form,
            "import_obj": imp,
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
