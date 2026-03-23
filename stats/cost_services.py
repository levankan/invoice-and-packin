from __future__ import annotations

from decimal import Decimal
from imports.models import Import
from django.db.models import Sum
from stats.exchange_rates import (
    fetch_nbg_rates_for_date,
    convert_to_usd,
    ExchangeRateError,
)

ZERO = Decimal("0")
SUPPORTED_CURRENCIES = {"USD", "EUR", "GEL", "GBP", "TRY", "ILS", "CNY"}


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

    return qs.distinct()


def _sum_goods_amount(import_obj: Import) -> Decimal:
    result = import_obj.lines.exclude(
        line_amount__isnull=True
    ).aggregate(total=Sum("line_amount"))["total"]

    return result if result is not None else ZERO


def _normalize_currency(code: str | None) -> str:
    return (code or "").upper().strip()


def _shipping_method_key(import_obj: Import) -> str:
    method = (import_obj.shipping_method or "").strip().lower()

    if method in {"air", "sea", "road", "courier"}:
        return method

    return "other"


def build_cost_analysis(date_from=None, date_to=None, vendor_name=None, item_no=None):
    qs = _declared_imports_queryset(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    ).prefetch_related("lines")

    rows = []
    cards = {
        "all": 0,
        "air": 0,
        "sea": 0,
        "road": 0,
        "courier": 0,
        "other": 0,
    }

    total_goods_usd = ZERO
    total_transport_usd = ZERO

    # cache NBG rates by date so we do not call API repeatedly for same date
    rates_cache: dict = {}

    for imp in qs:
        goods_amount = _sum_goods_amount(imp)
        transport_amount = imp.transport_price or ZERO

        goods_currency = _normalize_currency(imp.currency_code)
        transport_currency = _normalize_currency(imp.transport_currency)

        if goods_amount <= 0:
            continue

        if transport_amount <= 0:
            continue

        if not goods_currency or not transport_currency:
            continue

        if goods_currency not in SUPPORTED_CURRENCIES:
            continue

        if transport_currency not in SUPPORTED_CURRENCIES:
            continue

        declaration_date = imp.declaration_date
        if not declaration_date:
            continue

        if declaration_date not in rates_cache:
            try:
                rates_cache[declaration_date] = fetch_nbg_rates_for_date(declaration_date)
            except ExchangeRateError:
                rates_cache[declaration_date] = None

        rates = rates_cache.get(declaration_date)
        if not rates:
            continue

        try:
            goods_usd = convert_to_usd(goods_amount, goods_currency, rates)
            transport_usd = convert_to_usd(transport_amount, transport_currency, rates)
        except ExchangeRateError:
            continue

        if goods_usd <= 0:
            continue

        transport_percent = (transport_usd / goods_usd) * Decimal("100")
        method = _shipping_method_key(imp)

        cards["all"] += 1
        cards[method] += 1

        total_goods_usd += goods_usd
        total_transport_usd += transport_usd

        rows.append({
            "import_code": imp.import_code,
            "vendor_name": imp.vendor_name,
            "shipping_method": imp.shipping_method,
            "declaration_c_number": imp.declaration_c_number,
            "declaration_date": imp.declaration_date,
            "goods_amount": goods_amount,
            "goods_currency": goods_currency,
            "goods_usd": goods_usd.quantize(Decimal("0.01")),
            "transport_amount": transport_amount,
            "transport_currency": transport_currency,
            "transport_usd": transport_usd.quantize(Decimal("0.01")),
            "transport_percent": transport_percent.quantize(Decimal("0.01")),
        })

    overall_percent = ZERO
    if total_goods_usd > 0:
        overall_percent = (total_transport_usd / total_goods_usd) * Decimal("100")

    summary = {
        "total_goods_usd": total_goods_usd.quantize(Decimal("0.01")),
        "total_transport_usd": total_transport_usd.quantize(Decimal("0.01")),
        "overall_percent": overall_percent.quantize(Decimal("0.01")),
    }

    return {
        "cards": cards,
        "summary": summary,
        "rows": rows,
    }