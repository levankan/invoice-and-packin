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

    # helper to build packages_list / packages_json for this import
    def _build_packages_context(import_obj):
        packages_qs = ImportPackage.objects.filter(
            import_header=import_obj
        ).order_by("pk")

        packages_list = []
        for p in packages_qs:
            packages_list.append(
                {
                    "type": p.package_type or "",
                    "length": p.length_cm,
                    "width": p.width_cm,
                    "height": p.height_cm,
                    "gross_weight": p.gross_weight_kg,
                    "unit_system": p.unit_system or "metric",
                }
            )
        packages_json = json.dumps(packages_list, default=str)
        return packages_list, packages_json

    if request.method == "POST":
        form = ExporterCountryForm(request.POST)
        if form.is_valid():
            data = request.POST

            exporter_country = form.cleaned_data.get("exporter_country")

            forwarder_id = data.get("forwarder")
            forwarder = (
                Forwarder.objects.filter(pk=forwarder_id).first()
                if forwarder_id
                else None
            )

            incoterms = _clean(data.get("incoterms"))
            if incoterms:
                incoterms = incoterms.upper()

            tracking_no = _clean(data.get("tracking_no"))
            if tracking_no:
                tracking_no = tracking_no.upper()

            goods_price = None
            gp_raw = _clean(data.get("goods_price"))
            if gp_raw:
                try:
                    goods_price = Decimal(gp_raw)
                except InvalidOperation:
                    goods_price = None

            def _parse_date(key):
                v = _clean(data.get(key))
                if not v:
                    return None
                try:
                    return datetime.strptime(v, "%Y-%m-%d").date()
                except ValueError:
                    return None

            expected_receipt_date = _parse_date("expected_receipt_date")
            declaration_date = _parse_date("declaration_date")

            # --------- update header ----------
            imp.vendor_name = _clean(data.get("vendor_name")) or ""
            imp.exporter_country = exporter_country
            imp.incoterms = incoterms
            imp.currency_code = _clean(data.get("currency_code"))
            imp.goods_price = goods_price
            imp.tracking_no = tracking_no
            imp.shipping_method = _clean(data.get("shipping_method"))
            imp.shipment_status = _clean(data.get("shipment_status"))
            imp.pickup_address = _clean(data.get("pickup_address"))
            imp.is_danger = bool(data.get("is_danger"))
            imp.is_stackable = bool(data.get("is_stackable"))
            imp.expected_receipt_date = expected_receipt_date
            imp.notes = _clean(data.get("notes"))
            imp.vendor_reference = _clean(data.get("vendor_reference"))
            imp.forwarder_reference = _clean(data.get("forwarder_reference"))
            imp.declaration_c_number = _clean(data.get("declaration_c_number"))
            imp.declaration_a_number = _clean(data.get("declaration_a_number"))
            imp.declaration_date = declaration_date
            imp.forwarder = forwarder

            # --------- update packages from packages_json ----------
            packages_raw = data.get("packages_json")
            total_gw_kg = Decimal("0")
            total_vol_kg = Decimal("0")

            # clear old packages
            ImportPackage.objects.filter(import_header=imp).delete()

            if packages_raw:
                try:
                    packages = json.loads(packages_raw)
                except json.JSONDecodeError:
                    packages = []
                else:
                    INCH_TO_CM = Decimal("2.54")
                    LB_TO_KG = Decimal("0.45359237")
                    VOL_DIVISOR = Decimal("6000")

                    def to_decimal(value):
                        if value in (None, "", " "):
                            return None
                        try:
                            return Decimal(str(value))
                        except (InvalidOperation, TypeError):
                            return None

                    for p in packages:
                        p_type = (p.get("type") or "").upper() or None
                        unit_system = p.get("unit_system") or "metric"

                        length = to_decimal(p.get("length"))
                        width = to_decimal(p.get("width"))
                        height = to_decimal(p.get("height"))
                        gw = to_decimal(p.get("gross_weight"))

                        # convert imperial to metric
                        if unit_system == "imperial":
                            if length is not None:
                                length = (length * INCH_TO_CM).quantize(Decimal("0.01"))
                            if width is not None:
                                width = (width * INCH_TO_CM).quantize(Decimal("0.01"))
                            if height is not None:
                                height = (height * INCH_TO_CM).quantize(Decimal("0.01"))
                            if gw is not None:
                                gw = (gw * LB_TO_KG).quantize(Decimal("0.001"))
                            unit_system_db = "imperial"
                        else:
                            unit_system_db = "metric"

                        # create package row if anything is filled
                        if any([p_type, length, width, height, gw]):
                            ImportPackage.objects.create(
                                import_header=imp,
                                package_type=p_type,
                                length_cm=length,
                                width_cm=width,
                                height_cm=height,
                                gross_weight_kg=gw,
                                unit_system=unit_system_db,
                            )

                            if gw is not None:
                                total_gw_kg += gw

                            if (
                                length is not None
                                and width is not None
                                and height is not None
                            ):
                                vol_kg = (length * width * height) / VOL_DIVISOR
                                total_vol_kg += vol_kg

            # save totals
            imp.total_gross_weight_kg = total_gw_kg if total_gw_kg != 0 else None
            imp.total_volumetric_weight_kg = (
                total_vol_kg.quantize(Decimal("0.001")) if total_vol_kg != 0 else None
            )

            imp.save()
            return redirect("imports_home")
        else:
            # form invalid → show errors + existing packages
            packages_list, packages_json = _build_packages_context(imp)

            return render(
                request,
                "imports/register_imports.html",
                {
                    "created_import": None,
                    "vendors": vendors,
                    "forwarders": forwarders,
                    "form": form,
                    "import_obj": imp,
                    "lines_data": [],
                    "lines_json": "",
                    "form_data": {},
                    "packages_json": packages_json,
                    "packages_list": packages_list,
                },
            )
    else:
        form = ExporterCountryForm(initial={"exporter_country": imp.exporter_country})
        packages_list, packages_json = _build_packages_context(imp)

    # GET render
    return render(
        request,
        "imports/register_imports.html",
        {
            "created_import": None,
            "vendors": vendors,
            "forwarders": forwarders,
            "form": form,
            "import_obj": imp,
            "lines_data": [],
            "lines_json": "",
            "form_data": {},
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
