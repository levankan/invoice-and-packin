# imports/views/edit.py
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect

from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..models import Import
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
            imp.save()
            return redirect("imports_home")
    else:
        form = ExporterCountryForm(initial={"exporter_country": imp.exporter_country})

    return render(
        request,
        "imports/register_imports.html",
        {
            "created_import": None,
            "vendors": vendors,
            "forwarders": forwarders,
            "form": form,
            "import_obj": imp,
            "lines_data": [],      # for template compatibility
            "lines_json": "",
            "form_data": {},       # not needed when editing, but harmless
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

