from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .services import get_import_statistics
from django.contrib.auth.decorators import login_required
from django.shortcuts import render



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

    date_from = parse_date(date_from_str)
    date_to = parse_date(date_to_str)

    stats = get_import_statistics(date_from=date_from, date_to=date_to)

    context = {
        "stats": stats,
        "date_from": date_from_str,
        "date_to": date_to_str,
    }
    return render(request, "stats/dashboard.html", context)




@login_required
def main(request):
    return render(request, "stats/main.html")