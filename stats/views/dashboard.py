#stats/views/dashboard.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from stats.services import get_import_statistics
from stats.utils import parse_date, get_vendor_suggestions, get_item_suggestions


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

    context = {
        "stats": stats,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "vendor_name": vendor_name,
        "item_no": item_no,
        "vendor_suggestions": get_vendor_suggestions(),
        "item_suggestions": get_item_suggestions(),
    }

    return render(request, "stats/dashboard.html", context)
