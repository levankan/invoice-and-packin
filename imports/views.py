from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import Import
# at top of file
from decimal import Decimal, InvalidOperation
from datetime import datetime
# imports/views.py (top of file)
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Import
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Import
from admin_area.models import Vendor  # <-- add this import
from .forms import ExporterCountryForm
import csv
from django.http import HttpResponse






ALLOWED_ROLES = {'logistics', 'procurement', 'Other Employee'}

# Choice lists for filters (also used by the template)
STATUS_CHOICES = ["PLANNED", "PICKED_UP", "IN_TRANSIT", "AT_CUSTOMS", "DELIVERED", "CANCELLED"]
METHOD_CHOICES = ["AIR", "SEA", "ROAD", "COURIER", "OTHER"]

def has_imports_access(user):
    if getattr(user, 'is_superuser', False):
        return True
    role = getattr(user, 'role', None)
    return role in ALLOWED_ROLES

@login_required
@user_passes_test(has_imports_access)
def imports_dashboard(request):
    """
    Imports list with search (import_code/vendor/tracking), filters, and pagination.
    """
    q = (request.GET.get("q") or "").strip()
    status_f = (request.GET.get("status") or "").strip()
    method_f = (request.GET.get("method") or "").strip()

    qs = Import.objects.all()

    if q:
        qs = qs.filter(
            Q(import_code__icontains=q) |
            Q(vendor_name__icontains=q) |
            Q(tracking_no__icontains=q)
        )

    if status_f:
        qs = qs.filter(shipment_status=status_f)

    if method_f:
        qs = qs.filter(shipping_method=method_f)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 20)  # 20 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "status_f": status_f,
        "method_f": method_f,
        "STATUS_CHOICES": STATUS_CHOICES,
        "METHOD_CHOICES": METHOD_CHOICES,
    }
    return render(request, "imports/dashboard.html", ctx)

# imports/views.py
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Import
from admin_area.models import Vendor  # <-- add this import





# imports/views.py
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import Import
from admin_area.models import Vendor
from .forms import ExporterCountryForm


ALLOWED_ROLES = {'logistics', 'procurement', 'Other Employee'}

STATUS_CHOICES = ["PLANNED", "PICKED_UP", "IN_TRANSIT", "AT_CUSTOMS", "DELIVERED", "CANCELLED"]
METHOD_CHOICES = ["AIR", "SEA", "ROAD", "COURIER", "OTHER"]


def has_imports_access(user):
    if getattr(user, 'is_superuser', False):
        return True
    role = getattr(user, 'role', None)
    return role in ALLOWED_ROLES


@login_required
@user_passes_test(has_imports_access)
def imports_dashboard(request):
    q = (request.GET.get("q") or "").strip()
    status_f = (request.GET.get("status") or "").strip()
    method_f = (request.GET.get("method") or "").strip()

    qs = Import.objects.all()

    if q:
        qs = qs.filter(
            Q(import_code__icontains=q) |
            Q(vendor_name__icontains=q) |
            Q(tracking_no__icontains=q)
        )

    if status_f:
        qs = qs.filter(shipment_status=status_f)

    if method_f:
        qs = qs.filter(shipping_method=method_f)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "status_f": status_f,
        "method_f": method_f,
        "STATUS_CHOICES": STATUS_CHOICES,
        "METHOD_CHOICES": METHOD_CHOICES,
    }
    return render(request, "imports/dashboard.html", ctx)


@login_required
@user_passes_test(has_imports_access)
def register_import(request):
    # helper lives inside the function, so it's always in scope
    def _clean(val):
        """Strip string; return None if empty."""
        if val is None:
            return None
        s = str(val).strip()
        return s or None

    vendors = Vendor.objects.all().order_by("name")  # for dropdown
    form = ExporterCountryForm(request.POST or None)
    created_import = None

    if request.method == "POST" and form.is_valid():
        data = request.POST

        # exporter_country from the form (django-countries)
        exporter_country = form.cleaned_data.get("exporter_country")  # will be code like "US" / "GE" or None

        # normalize strings
        incoterms = _clean(data.get("incoterms"))
        if incoterms:
            incoterms = incoterms.upper()

        tracking_no = _clean(data.get("tracking_no"))
        if tracking_no:
            tracking_no = tracking_no.upper()

        # safe decimal
        goods_price = None
        gp_raw = _clean(data.get("goods_price"))
        if gp_raw:
            try:
                goods_price = Decimal(gp_raw)
            except InvalidOperation:
                goods_price = None

        # safe date parser
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

        created_import = Import.objects.create(
            vendor_name=_clean(data.get("vendor_name")) or "",
            exporter_country=exporter_country,  # <-- from form
            incoterms=incoterms,
            currency_code=_clean(data.get("currency_code")),
            goods_price=goods_price,
            tracking_no=tracking_no,
            shipping_method=_clean(data.get("shipping_method")),
            shipment_status=_clean(data.get("shipment_status")),
            pickup_address=_clean(data.get("pickup_address")),
            is_danger=bool(data.get("is_danger")),
            is_stackable=bool(data.get("is_stackable")),
            expected_receipt_date=expected_receipt_date,
            notes=_clean(data.get("notes")),
            declaration_c_number=_clean(data.get("declaration_c_number")),
            declaration_a_number=_clean(data.get("declaration_a_number")),
            declaration_date=declaration_date,
        )

    return render(
        request,
        "imports/register_imports.html",
        {
            "created_import": created_import,
            "vendors": vendors,
            "form": form,   # <-- important for {{ form.exporter_country }}
        },
    )







@login_required
@user_passes_test(has_imports_access)
def export_imports_excel(request):
    """
    Export imports (with same filters as dashboard) to CSV (Excel-friendly).
    """
    q = (request.GET.get("q") or "").strip()
    status_f = (request.GET.get("status") or "").strip()
    method_f = (request.GET.get("method") or "").strip()

    qs = Import.objects.all()

    if q:
        qs = qs.filter(
            Q(import_code__icontains=q) |
            Q(vendor_name__icontains=q) |
            Q(tracking_no__icontains=q)
        )

    if status_f:
        qs = qs.filter(shipment_status=status_f)

    if method_f:
        qs = qs.filter(shipping_method=method_f)

    qs = qs.order_by("-created_at")

    # Prepare HTTP response as CSV
    response = HttpResponse(content_type="text/csv")
    filename = "imports_export.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    # Header row
    writer.writerow([
        "Import Code",
        "Vendor",
        "Exporter Country",
        "Incoterms",
        "Shipping Method",
        "Shipment Status",
        "Tracking Number",
        "Declaration C Number",
        "Declaration A Number",
        "Declaration Date",
        "Expected Receipt Date",
        "Created At",
    ])

    # Data rows
    for imp in qs:
        writer.writerow([
            imp.import_code,
            imp.vendor_name or "",
            imp.exporter_country or "",
            imp.incoterms or "",
            imp.shipping_method or "",
            imp.shipment_status or "",
            imp.tracking_no or "",
            imp.declaration_c_number or "",
            imp.declaration_a_number or "",
            imp.declaration_date.isoformat() if imp.declaration_date else "",
            imp.expected_receipt_date.isoformat() if imp.expected_receipt_date else "",
            imp.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    return response
