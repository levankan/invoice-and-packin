from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from imports.models import Import, ImportLine
from stats.services import get_import_statistics


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def dashboard(request):
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")
    vendor_name = request.GET.get("vendor_name", "").strip()
    item_no = request.GET.get("item_no", "").strip()

    date_from = parse_date(date_from_str)
    date_to = parse_date(date_to_str)

    stats = get_import_statistics(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

    vendor_suggestions = (
        Import.objects.exclude(vendor_name__isnull=True)
        .exclude(vendor_name__exact="")
        .values_list("vendor_name", flat=True)
        .distinct()
        .order_by("vendor_name")[:300]
    )

    item_suggestions = (
        ImportLine.objects.exclude(item_no__isnull=True)
        .exclude(item_no__exact="")
        .values_list("item_no", flat=True)
        .distinct()
        .order_by("item_no")[:300]
    )

    context = {
        "stats": stats,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "vendor_name": vendor_name,
        "item_no": item_no,
        "vendor_suggestions": vendor_suggestions,
        "item_suggestions": item_suggestions,
    }

    return render(request, "stats/dashboard.html", context)