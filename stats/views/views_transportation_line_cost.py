from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from imports.models import Import
from stats.exchange_rates import (
    fetch_nbg_rates_for_date,
    convert_to_usd,
    ExchangeRateError,
)

ZERO = Decimal("0")
TRANSPORTATION_ITEM_NO = "TRANSPORTATION"
SUPPORTED_CURRENCIES = {"USD", "EUR", "GEL", "GBP", "TRY", "ILS", "CNY"}


def _safe_decimal(value) -> Decimal:
    if value in (None, "", " "):
        return ZERO
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ZERO


def _normalize_currency(code: Optional[str]) -> str:
    if not code:
        return "USD"
    return str(code).strip().upper()


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

    currency_code = _normalize_currency(currency_code)
    if currency_code not in SUPPORTED_CURRENCIES:
        return ZERO

    return _safe_decimal(convert_to_usd(amount, currency_code, rates))


def build_transportation_line_fallback_analysis(
    date_from=None,
    date_to=None,
    vendor_name=None,
    item_no=None,
):
    qs = _declared_imports_queryset(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

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
        "rows": [],
        "errors": [],
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
            rate_cache[declaration_date] = fetch_nbg_rates_for_date(declaration_date)
        except ExchangeRateError as exc:
            result["errors"].append(f"{declaration_date}: {exc}")
            failed_dates.add(declaration_date)
        except Exception as exc:
            result["errors"].append(
                f"{declaration_date}: unexpected exchange-rate error: {exc}"
            )
            failed_dates.add(declaration_date)

    for imp in qs:
        header_transport_price = _safe_decimal(imp.transport_price)

        # Run fallback only when header transport is empty/zero
        if header_transport_price > ZERO:
            continue

        declaration_date = imp.declaration_date
        if not declaration_date:
            continue

        if declaration_date in failed_dates:
            continue

        rates = rate_cache.get(declaration_date)
        if not rates:
            continue

        line_currency = _normalize_currency(imp.currency_code or "USD")

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

        if transportation_line_count == 0:
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

        result["rows"].append(
            {
                "import_code": imp.import_code,
                "vendor_name": imp.vendor_name or "",
                "shipping_method": imp.shipping_method or "",
                "declaration_c_number": imp.declaration_c_number or "",
                "declaration_date": imp.declaration_date,
                "currency_code": line_currency,
                "transportation_line_count": transportation_line_count,
                "total_lines_amount": total_lines_amount.quantize(Decimal("0.01")),
                "transportation_lines_amount": transportation_lines_amount.quantize(Decimal("0.01")),
                "goods_amount": goods_amount.quantize(Decimal("0.01")),
                "total_lines_usd": total_lines_usd.quantize(Decimal("0.01")),
                "transport_usd": transport_usd.quantize(Decimal("0.01")),
                "goods_usd": goods_usd.quantize(Decimal("0.01")),
                "percent": percent.quantize(Decimal("0.01")),
            }
        )

    total_goods_usd = result["summary"]["total_goods_usd"]
    total_transport_usd = result["summary"]["total_transport_usd"]

    overall_percent = ZERO
    if total_goods_usd > ZERO:
        overall_percent = (total_transport_usd / total_goods_usd) * Decimal("100")

    result["summary"]["total_goods_usd"] = total_goods_usd.quantize(Decimal("0.01"))
    result["summary"]["total_transport_usd"] = total_transport_usd.quantize(Decimal("0.01"))
    result["summary"]["overall_percent"] = overall_percent.quantize(Decimal("0.01"))

    result["rows"] = sorted(
        result["rows"],
        key=lambda x: (x["declaration_date"] or "", x["import_code"]),
        reverse=True,
    )

    return result