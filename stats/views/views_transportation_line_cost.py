from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from imports.models import Import
from stats.constants import ZERO, TWO_PLACES, SUPPORTED_CURRENCIES, TRANSPORTATION_ITEM_NO
from stats.exchange_rates import (
    get_nbg_rates_for_date,
    convert_to_usd,
    ExchangeRateError,
)
from stats.utils import normalize_currency


def _safe_decimal(value) -> Decimal:
    if value in (None, "", " "):
        return ZERO
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ZERO



def _declared_imports_queryset(date_from=None, date_to=None, vendor_name=None, item_no=None):
    qs = Import.objects.filter(
        declaration_c_number__isnull=False,
        declaration_date__isnull=False,
    ).exclude(
        declaration_c_number__exact=""
    )

    if date_from:
        qs = qs.filter(declaration_date__gte=date_from)
    if date_to:
        qs = qs.filter(declaration_date__lte=date_to)
    if vendor_name:
        qs = qs.filter(vendor_name__icontains=vendor_name)
    if item_no:
        qs = qs.filter(lines__item_no__icontains=item_no)

    return qs.distinct().prefetch_related("lines")


def _shipping_method_bucket(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()

    if "air" in raw:
        return "air"
    if "sea" in raw or "ocean" in raw or "vessel" in raw:
        return "sea"
    if "road" in raw or "truck" in raw or "land" in raw:
        return "road"
    if any(x in raw for x in ["courier", "fedex", "dhl", "ups", "tnt", "aramex"]):
        return "courier"
    return "other"


def _convert_amount_to_usd(amount: Decimal, currency_code: str, rates) -> Decimal:
    amount = _safe_decimal(amount)
    if amount <= ZERO:
        return ZERO

    currency_code = normalize_currency(currency_code)
    if currency_code not in SUPPORTED_CURRENCIES:
        return ZERO

    return _safe_decimal(convert_to_usd(amount, currency_code, rates))


def build_transportation_line_fallback_analysis(
    date_from=None,
    date_to=None,
    vendor_name=None,
    item_no=None,
    include_rows=False,
):
    qs = _declared_imports_queryset(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

    warnings = {"skipped": [], "soft": [], "info": []}

    rows = []

    result = {
        "cards": {
            "all": 0,
            "air": 0,
            "sea": 0,
            "road": 0,
            "courier": 0,
            "other": 0,
        },
        "summary": {
            "total_goods_usd": Decimal("0.00"),
            "total_transport_usd": Decimal("0.00"),
            "overall_percent": Decimal("0.00"),
        },
        "warnings": warnings,
    }

    # Preload unique declaration dates once
    declaration_dates = {
        imp.declaration_date
        for imp in qs
        if imp.declaration_date
    }

    rate_cache = {}
    failed_dates = set()

    for declaration_date in declaration_dates:
        try:
            rate_cache[declaration_date] = get_nbg_rates_for_date(declaration_date)
        except ExchangeRateError as exc:
            warnings["skipped"].append({
                "import_code": None,
                "reason": f"exchange rate unavailable for {declaration_date}: {exc}",
            })
            failed_dates.add(declaration_date)
        except Exception as exc:
            warnings["skipped"].append({
                "import_code": None,
                "reason": f"exchange rate unavailable for {declaration_date}: unexpected error: {exc}",
            })
            failed_dates.add(declaration_date)

    for imp in qs:
        header_transport_price = _safe_decimal(imp.transport_price)

        # Info: imports with a header transport price belong to the standard
        # analysis, not fallback. This is an expected exclusion, not an error.
        if header_transport_price > ZERO:
            warnings["info"].append({
                "import_code": imp.import_code,
                "reason": "has header transport price — handled by standard analysis",
            })
            continue

        declaration_date = imp.declaration_date
        if not declaration_date:
            continue

        if declaration_date in failed_dates:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": f"exchange rate unavailable for {declaration_date}",
            })
            continue

        rates = rate_cache.get(declaration_date)
        if not rates:
            continue

        line_currency = normalize_currency(imp.currency_code)
        if not line_currency:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "currency code missing",
            })
            continue

        total_lines_amount = ZERO
        transportation_lines_amount = ZERO
        transportation_line_count = 0

        for line in imp.lines.all():
            line_amount = _safe_decimal(line.line_amount)
            if line_amount <= ZERO:
                continue

            total_lines_amount += line_amount

            if (line.item_no or "").strip().upper() == TRANSPORTATION_ITEM_NO:
                transportation_lines_amount += line_amount
                transportation_line_count += 1

        # Soft: no TRANSPORTATION lines means we cannot determine transport
        # cost via this method. Import is excluded but this is not an error.
        if transportation_line_count == 0:
            warnings["soft"].append({
                "import_code": imp.import_code,
                "reason": "no TRANSPORTATION lines found — excluded from fallback",
            })
            continue

        goods_amount = total_lines_amount - transportation_lines_amount
        if goods_amount < ZERO:
            goods_amount = ZERO

        transport_usd = _convert_amount_to_usd(
            transportation_lines_amount, line_currency, rates
        )
        goods_usd = _convert_amount_to_usd(goods_amount, line_currency, rates)
        total_lines_usd = _convert_amount_to_usd(total_lines_amount, line_currency, rates)

        percent = ZERO
        if goods_usd > ZERO:
            percent = (transport_usd / goods_usd) * Decimal("100")

        bucket = _shipping_method_bucket(imp.shipping_method)

        result["cards"]["all"] += 1
        result["cards"][bucket] += 1

        result["summary"]["total_goods_usd"] += goods_usd
        result["summary"]["total_transport_usd"] += transport_usd

        if include_rows:
            rows.append(
                {
                    "import_code": imp.import_code,
                    "vendor_name": imp.vendor_name or "",
                    "shipping_method": imp.shipping_method or "",
                    "declaration_c_number": imp.declaration_c_number or "",
                    "declaration_date": imp.declaration_date,
                    "currency_code": line_currency,
                    "transportation_line_count": transportation_line_count,
                    "total_lines_amount": total_lines_amount.quantize(TWO_PLACES),
                    "transportation_lines_amount": transportation_lines_amount.quantize(TWO_PLACES),
                    "goods_amount": goods_amount.quantize(TWO_PLACES),
                    "total_lines_usd": total_lines_usd.quantize(TWO_PLACES),
                    "transport_usd": transport_usd.quantize(TWO_PLACES),
                    "goods_usd": goods_usd.quantize(TWO_PLACES),
                    "percent": percent.quantize(TWO_PLACES),
                }
            )

    total_goods_usd = result["summary"]["total_goods_usd"]
    total_transport_usd = result["summary"]["total_transport_usd"]

    overall_percent = ZERO
    if total_goods_usd > ZERO:
        overall_percent = (total_transport_usd / total_goods_usd) * Decimal("100")

    result["summary"]["total_goods_usd"] = total_goods_usd.quantize(TWO_PLACES)
    result["summary"]["total_transport_usd"] = total_transport_usd.quantize(TWO_PLACES)
    result["summary"]["overall_percent"] = overall_percent.quantize(TWO_PLACES)

    if include_rows:
        result["rows"] = sorted(
            rows,
            key=lambda x: (x["declaration_date"] or "", x["import_code"]),
            reverse=True,
        )

    return result