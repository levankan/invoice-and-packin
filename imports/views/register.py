# imports/views/register.py
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect

from admin_area.models import Forwarder, Vendor
from ..forms import ExporterCountryForm
from ..models import Import, ImportLine, ImportPackage
from ..permissions import has_imports_access

@login_required
@user_passes_test(has_imports_access)
def register_import(request):
    vendors = Vendor.objects.all().order_by("name")
    forwarders = Forwarder.objects.all().order_by("name")

    def _clean(val):
        if val is None:
            return None
        s = str(val).strip()
        return s or None

    def _parse_date_str(s):
        s = _clean(s)
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None

    lines_data = []
    lines_json = ""
    form_data = {}
    packages_json = ""
    packages_list = []

    if request.method == "POST":
        action = request.POST.get("action", "save_import")
        form = ExporterCountryForm(request.POST)

        if form.is_valid():
            data = request.POST
            exporter_country = form.cleaned_data.get("exporter_country")

            # ✅✅✅ SAFE FORWARDER RESOLUTION (THIS FIXES YOUR ERROR)
            transport_forwarder = (
                Forwarder.objects.filter(pk=data.get("transport_forwarder")).first()
                if data.get("transport_forwarder") else None
            )

            brokerage_forwarder = (
                Forwarder.objects.filter(pk=data.get("brokerage_forwarder")).first()
                if data.get("brokerage_forwarder") else None
            )

            internal_delivery_forwarder = (
                Forwarder.objects.filter(pk=data.get("internal_delivery_forwarder")).first()
                if data.get("internal_delivery_forwarder") else None
            )

            other1_forwarder = (
                Forwarder.objects.filter(pk=data.get("other1_forwarder")).first()
                if data.get("other1_forwarder") else None
            )

            other2_forwarder = (
                Forwarder.objects.filter(pk=data.get("other2_forwarder")).first()
                if data.get("other2_forwarder") else None
            )

            main_forwarder = (
                Forwarder.objects.filter(pk=data.get("forwarder")).first()
                if data.get("forwarder") else None
            )

            def _dec_or_none(key):
                raw = _clean(data.get(key))
                if not raw:
                    return None
                try:
                    return Decimal(raw)
                except InvalidOperation:
                    return None

            # ✅✅✅ CREATE IMPORT (NOW VARIABLES EXIST)
            imp = Import.objects.create(
                vendor_name=_clean(data.get("vendor_name")) or "",
                exporter_country=exporter_country,
                incoterms=(_clean(data.get("incoterms")) or "").upper() if _clean(data.get("incoterms")) else None,
                currency_code=_clean(data.get("currency_code")),
                goods_price=_dec_or_none("goods_price"),
                tracking_no=(_clean(data.get("tracking_no")) or "").upper() if _clean(data.get("tracking_no")) else None,
                shipping_method=_clean(data.get("shipping_method")),
                shipment_status=_clean(data.get("shipment_status")),
                pickup_address=_clean(data.get("pickup_address")),
                is_danger=bool(data.get("is_danger")),
                is_stackable=bool(data.get("is_stackable")),
                expected_receipt_date=_parse_date_str(data.get("expected_receipt_date")),
                notes=_clean(data.get("notes")),
                vendor_reference=_clean(data.get("vendor_reference")),
                forwarder_reference=_clean(data.get("forwarder_reference")),
                declaration_c_number=_clean(data.get("declaration_c_number")),
                declaration_a_number=_clean(data.get("declaration_a_number")),
                declaration_date=_parse_date_str(data.get("declaration_date")),
                forwarder=main_forwarder,

                transport_invoice_no=_clean(data.get("transport_invoice_no")),
                transport_price=_dec_or_none("transport_price"),
                transport_currency=_clean(data.get("transport_currency")),
                transport_payment_date=_parse_date_str(data.get("transport_payment_date")),
                transport_forwarder=transport_forwarder,

                brokerage_invoice_no=_clean(data.get("brokerage_invoice_no")),
                brokerage_price=_dec_or_none("brokerage_price"),
                brokerage_currency=_clean(data.get("brokerage_currency")),
                brokerage_payment_date=_parse_date_str(data.get("brokerage_payment_date")),
                brokerage_forwarder=brokerage_forwarder,

                internal_delivery_invoice_no=_clean(data.get("internal_delivery_invoice_no")),
                internal_delivery_price=_dec_or_none("internal_delivery_price"),
                internal_delivery_currency=_clean(data.get("internal_delivery_currency")),
                internal_delivery_payment_date=_parse_date_str(data.get("internal_delivery_payment_date")),
                internal_delivery_forwarder=internal_delivery_forwarder,

                other1_invoice_no=_clean(data.get("other1_invoice_no")),
                other1_price=_dec_or_none("other1_price"),
                other1_currency=_clean(data.get("other1_currency")),
                other1_payment_date=_parse_date_str(data.get("other1_payment_date")),
                other1_forwarder=other1_forwarder,

                other2_invoice_no=_clean(data.get("other2_invoice_no")),
                other2_price=_dec_or_none("other2_price"),
                other2_currency=_clean(data.get("other2_currency")),
                other2_payment_date=_parse_date_str(data.get("other2_payment_date")),
                other2_forwarder=other2_forwarder,
            )

            messages.success(request, f"Import {imp.import_code} created successfully.")
            return redirect("imports_home")

    form = ExporterCountryForm()
    return render(
        request,
        "imports/register_imports.html",
        {
            "vendors": vendors,
            "forwarders": forwarders,
            "form": form,
            "import_obj": None,
        },
    )
