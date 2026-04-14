from datetime import datetime

from django.utils.text import slugify
from imports.models import Import, ImportLine


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def get_vendor_suggestions():
    return (
        Import.objects.exclude(vendor_name__isnull=True)
        .exclude(vendor_name__exact="")
        .values_list("vendor_name", flat=True)
        .distinct()
        .order_by("vendor_name")[:300]
    )


def get_item_suggestions():
    return (
        ImportLine.objects.exclude(item_no__isnull=True)
        .exclude(item_no__exact="")
        .values_list("item_no", flat=True)
        .distinct()
        .order_by("item_no")[:300]
    )


def normalize_currency(code) -> str:
    if not code:
        return ""
    return str(code).strip().upper()


def build_export_filename(prefix, date_from_str, date_to_str, vendor_name, item_no):
    parts = [prefix]
    if date_from_str and date_to_str:
        parts.append(f"{date_from_str}_to_{date_to_str}")
    elif date_from_str:
        parts.append(f"from_{date_from_str}")
    elif date_to_str:
        parts.append(f"to_{date_to_str}")
    if vendor_name:
        parts.append(f"vendor_{slugify(vendor_name)}")
    if item_no:
        parts.append(f"item_{slugify(item_no)}")
    return "_".join(parts) + ".xlsx"
