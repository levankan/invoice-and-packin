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

    # defaults
    lines_data = []
    lines_json = ""
    form_data = {}
    packages_json = ""
    packages_list = []

    if request.method == "POST":
        action = request.POST.get("action", "save_import")
        form = ExporterCountryForm(request.POST)

        # --- preserve form fields so template can refill on error or re-render ---
        form_data = {
            "vendor_name": request.POST.get("vendor_name", ""),
            "incoterms": request.POST.get("incoterms", ""),
            "currency_code": request.POST.get("currency_code", ""),
            "goods_price": request.POST.get("goods_price", ""),
            "shipping_method": request.POST.get("shipping_method", ""),
            "forwarder": request.POST.get("forwarder", ""),
            "shipment_status": request.POST.get("shipment_status", ""),
            "tracking_no": request.POST.get("tracking_no", ""),
            "vendor_reference": request.POST.get("vendor_reference", ""),
            "forwarder_reference": request.POST.get("forwarder_reference", ""),
            "is_danger": bool(request.POST.get("is_danger")),
            "is_stackable": bool(request.POST.get("is_stackable")),
            "pickup_address": request.POST.get("pickup_address", ""),
            "expected_receipt_date": request.POST.get("expected_receipt_date", ""),
            "declaration_c_number": request.POST.get("declaration_c_number", ""),
            "declaration_a_number": request.POST.get("declaration_a_number", ""),
            "declaration_date": request.POST.get("declaration_date", ""),
            "notes": request.POST.get("notes", ""),
        }

        # --- restore existing lines from hidden JSON (if any) ---
        existing_lines_json = request.POST.get("lines_json") or ""
        if existing_lines_json:
            try:
                lines_data = json.loads(existing_lines_json)
            except json.JSONDecodeError:
                lines_data = []
        lines_json = existing_lines_json

        # --- restore existing packages from hidden JSON (if any) ---
        packages_json = request.POST.get("packages_json") or ""
        if packages_json:
            try:
                packages_list = json.loads(packages_json)
            except json.JSONDecodeError:
                packages_list = []
        else:
            packages_list = []

        # ---------------------------------------------------------------------
        #  UPLOAD LINES (preview only; DB save happens when we press Save)
        # ---------------------------------------------------------------------
        if action == "upload_lines":
            upload = request.FILES.get("lines_file")
            if not upload:
                messages.error(request, "Please choose an Excel file to upload.")
            else:
                try:
                    wb = openpyxl.load_workbook(upload, data_only=True)
                    sheet = wb.active

                    # fixed columns order:
                    # Document No., Line No., No., Description, Quantity,
                    # Unit of Measure, Direct Unit Cost Excl. VAT,
                    # Line Amount Excl. VAT, Expected Receipt Date, Delivery Date
                    lines_data = []

                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        if not any(row):
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
                            *_
                        ) = (list(row) + [None] * 10)[:10]

                        def _as_str(x):
                            return "" if x is None else str(x).strip()

                        def _as_dec(x):
                            try:
                                return Decimal(str(x)) if x not in (None, "") else None
                            except InvalidOperation:
                                return None

                        def _as_date(x):
                            if isinstance(x, datetime):
                                return x.date().isoformat()
                            if isinstance(x, str):
                                x = x.strip()
                                if not x:
                                    return ""
                                for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                                    try:
                                        return datetime.strptime(x, fmt).date().isoformat()
                                    except ValueError:
                                        continue
                            return ""

                        lines_data.append(
                            {
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
                            }
                        )

                    messages.success(
                        request,
                        f"{len(lines_data)} line(s) loaded from Excel. "
                        f"They will be saved when you press Save."
                    )

                except Exception as e:
                    messages.error(request, f"Error reading Excel: {e}")
                    lines_data = []

            # re-encode latest lines_data into hidden JSON
            lines_json = json.dumps(lines_data, default=str)

            return render(
                request,
                "imports/register_imports.html",
                {
                    "created_import": None,
                    "vendors": vendors,
                    "forwarders": forwarders,
                    "form": form,
                    "import_obj": None,
                    "lines_data": lines_data,
                    "lines_json": lines_json,
                    "form_data": form_data,
                    # 🔹 keep packages visible after upload_lines
                    "packages_json": packages_json,
                    "packages_list": packages_list,
                },
            )

        # ---------------------------------------------------------------------
        #  SAVE IMPORT + SAVE LINES TO DB
        # ---------------------------------------------------------------------
        if form.is_valid():
            data = request.POST
            exporter_country = form.cleaned_data.get("exporter_country")

            # forwarder FK
            forwarder_id = data.get("forwarder")
            forwarder = (
                Forwarder.objects.filter(pk=forwarder_id).first()
                if forwarder_id
                else None
            )

            def _dec_or_none(key):
                raw = _clean(data.get(key))
                if not raw:
                    return None
                try:
                    return Decimal(raw)
                except InvalidOperation:
                    return None

            # --- create Import header ---
            imp = Import.objects.create(
                vendor_name=_clean(data.get("vendor_name")) or "",
                exporter_country=exporter_country,
                incoterms=(_clean(data.get("incoterms")) or "").upper()
                if _clean(data.get("incoterms"))
                else None,
                currency_code=_clean(data.get("currency_code")),
                goods_price=_dec_or_none("goods_price"),
                tracking_no=(_clean(data.get("tracking_no")) or "").upper()
                if _clean(data.get("tracking_no"))
                else None,
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
                forwarder=forwarder,
            )

            # --- handle packages_json -> ImportPackage + totals ---
            packages_raw = data.get("packages_json")
            total_gw_kg = Decimal("0")
            total_vol_kg = Decimal("0")

            if packages_raw:
                try:
                    packages = json.loads(packages_raw)
                except json.JSONDecodeError:
                    packages = []

                INCH_TO_CM = Decimal("2.54")
                LB_TO_KG = Decimal("0.45359237")
                VOL_DIVISOR = Decimal("6000")  # cm³ / kg

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

            # save totals on header
            imp.total_gross_weight_kg = total_gw_kg if total_gw_kg != 0 else None
            imp.total_volumetric_weight_kg = (
                total_vol_kg.quantize(Decimal("0.001")) if total_vol_kg != 0 else None
            )
            imp.save()

            # --- re-parse lines_json directly from POST (extra safety) ---
            lines_json_str = request.POST.get("lines_json") or ""
            try:
                lines_data_for_save = json.loads(lines_json_str) if lines_json_str else []
            except json.JSONDecodeError:
                lines_data_for_save = []

            # --- create ImportLine rows from lines_data_for_save ---
            if lines_data_for_save:
                for l in lines_data_for_save:
                    ImportLine.objects.create(
                        import_header=imp,
                        document_no=l.get("document_no") or "",
                        line_no=l.get("line_no") or "",
                        item_no=l.get("item_no") or "",
                        description=l.get("description") or "",
                        quantity=l.get("quantity"),
                        unit_of_measure=l.get("unit_of_measure") or "",
                        unit_cost=l.get("unit_cost"),
                        line_amount=l.get("line_amount"),
                        expected_receipt_date=_parse_date_str(
                            l.get("expected_receipt_date")
                        ),
                        delivery_date=_parse_date_str(l.get("delivery_date")),
                    )

            messages.success(
                request,
                f"Import {imp.import_code} created together with {len(lines_data_for_save)} line(s).",
            )
            return redirect("imports_home")

        # ---------------------------------------------------------------------
        #  FORM INVALID → re-render with errors and keep lines & packages
        # ---------------------------------------------------------------------
        lines_json = json.dumps(lines_data, default=str)
        return render(
            request,
            "imports/register_imports.html",
            {
                "created_import": None,
                "vendors": vendors,
                "forwarders": forwarders,
                "form": form,
                "import_obj": None,
                "lines_data": lines_data,
                "lines_json": lines_json,
                "form_data": form_data,
                "packages_json": packages_json,
                "packages_list": packages_list,
            },
        )

    # -------------------------------------------------------------------------
    # GET
    # -------------------------------------------------------------------------
    form = ExporterCountryForm()
    return render(
        request,
        "imports/register_imports.html",
        {
            "created_import": None,
            "vendors": vendors,
            "forwarders": forwarders,
            "form": form,
            "import_obj": None,
            "lines_data": [],
            "lines_json": "",
            "form_data": {},
            "packages_json": "",
            "packages_list": [],
        },
    )
