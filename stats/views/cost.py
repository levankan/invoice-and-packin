from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from stats.cost_services import build_cost_analysis, build_unified_cost_analysis
from stats.utils import parse_date, get_vendor_suggestions, get_item_suggestions
from .views_transportation_line_cost import build_transportation_line_fallback_analysis


@login_required
def cost_analysis(request):
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")
    vendor_name = request.GET.get("vendor_name", "").strip()
    item_no = request.GET.get("item_no", "").strip()

    date_from = parse_date(date_from_str)
    date_to = parse_date(date_to_str)

    today = date.today()
    if date_from is None:
        date_from = today.replace(day=1)
        date_from_str = date_from.strftime("%Y-%m-%d")
    if date_to is None:
        date_to = today
        date_to_str = today.strftime("%Y-%m-%d")

    data = build_cost_analysis(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

    fallback_analysis = build_transportation_line_fallback_analysis(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

    unified_analysis = build_unified_cost_analysis(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

    # ------------------------------------------------------------------
    # Merge warnings from all three analyses into one top-level structure.
    # Exchange-rate failures are pulled out of each analysis's skipped list,
    # deduplicated by date, and recorded with which analyses were affected.
    # The remaining per-analysis warnings stay grouped under their analysis.
    # ------------------------------------------------------------------
    _rate_failures_by_date = {}

    def _pull_rate_failures(skipped_list, analysis_name):
        """Return (remaining_skipped, side-effect: populate _rate_failures_by_date)."""
        remaining = []
        for entry in skipped_list:
            reason = entry.get("reason", "")
            if reason.startswith("exchange rate unavailable for "):
                # Date token sits immediately after the prefix, before any ":"
                date_key = reason[len("exchange rate unavailable for "):].split(":")[0].strip()
                if date_key not in _rate_failures_by_date:
                    _rate_failures_by_date[date_key] = {"date": date_key, "analyses": []}
                if analysis_name not in _rate_failures_by_date[date_key]["analyses"]:
                    _rate_failures_by_date[date_key]["analyses"].append(analysis_name)
            else:
                remaining.append(entry)
        return remaining

    std_skipped = _pull_rate_failures(data["warnings"]["skipped"],              "standard")
    fb_skipped  = _pull_rate_failures(fallback_analysis["warnings"]["skipped"], "fallback")
    uni_skipped = _pull_rate_failures(unified_analysis["warnings"]["skipped"],  "unified")

    warnings = {
        "exchange_rate_failures": list(_rate_failures_by_date.values()),
        "standard": {
            "skipped": std_skipped,
            "soft":    data["warnings"]["soft"],
            "info":    data["warnings"]["info"],
        },
        "fallback": {
            "skipped": fb_skipped,
            "soft":    fallback_analysis["warnings"]["soft"],
            "info":    fallback_analysis["warnings"]["info"],
        },
        "unified": {
            "skipped": uni_skipped,
            "soft":    unified_analysis["warnings"]["soft"],
            "info":    unified_analysis["warnings"]["info"],
        },
    }

    has_warnings = bool(
        warnings["exchange_rate_failures"]
        or warnings["standard"]["skipped"]
        or warnings["standard"]["soft"]
        or warnings["standard"]["info"]
        or warnings["fallback"]["skipped"]
        or warnings["fallback"]["soft"]
        or warnings["fallback"]["info"]
        or warnings["unified"]["skipped"]
        or warnings["unified"]["soft"]
        or warnings["unified"]["info"]
    )

    context = {
        "analysis": data,
        "fallback_analysis": fallback_analysis,
        "unified_analysis": unified_analysis,
        "warnings": warnings,
        "has_warnings": has_warnings,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "vendor_name": vendor_name,
        "item_no": item_no,
        "vendor_suggestions": get_vendor_suggestions(),
        "item_suggestions": get_item_suggestions(),
    }
    return render(request, "stats/cost_analysis.html", context)
