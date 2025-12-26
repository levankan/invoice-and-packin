from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from ..models import Import
from ..permissions import has_imports_access, STATUS_CHOICES, METHOD_CHOICES


@login_required
#@user_passes_test(has_imports_access)
def imports_dashboard(request):
    q = (request.GET.get("q") or "").strip()

    # multiple statuses + multiple methods
    status_f = request.GET.getlist("status")  # list
    method_f = request.GET.getlist("method")  # list

    qs = (
        Import.objects
        .select_related("forwarder")
        .prefetch_related("lines")
        .order_by("-created_at")
    )

    if q:
        qs = qs.filter(
            Q(import_code__icontains=q)
            | Q(vendor_name__icontains=q)
            | Q(tracking_no__icontains=q)
            | Q(vendor_reference__icontains=q)
            | Q(forwarder_reference__icontains=q)
            | Q(lines__item_no__icontains=q)
            | Q(lines__document_no__icontains=q)
        ).distinct()

    if status_f:
        qs = qs.filter(shipment_status__in=status_f)

    if method_f:
        qs = qs.filter(shipping_method__in=method_f)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # keep selected statuses and methods in pagination links
    status_qs = "&".join(f"status={s}" for s in status_f)
    method_qs = "&".join(f"method={m}" for m in method_f)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "status_f": status_f,     # list
        "method_f": method_f,     # list
        "status_qs": status_qs,
        "method_qs": method_qs,
        "STATUS_CHOICES": STATUS_CHOICES,
        "METHOD_CHOICES": METHOD_CHOICES,
    }
    return render(request, "imports/dashboard.html", ctx)
