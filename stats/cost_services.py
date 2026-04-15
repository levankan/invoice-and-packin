from __future__ import annotations

from decimal import Decimal
from imports.models import Import
from django.db.models import Sum
from stats.constants import ZERO, TWO_PLACES, SUPPORTED_CURRENCIES, TRANSPORTATION_ITEM_NO
from stats.exchange_rates import (
    get_nbg_rates_for_date,
    convert_to_usd,
    ExchangeRateError,
)
from stats.utils import normalize_currency


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



def _shipping_method_key(import_obj: Import) -> str:
    method = (import_obj.shipping_method or "").strip().lower()

    if method in {"air", "sea", "road", "courier"}:
        return method

    return "other"


def build_cost_analysis(date_from=None, date_to=None, vendor_name=None, item_no=None, include_rows=False):
    qs = _declared_imports_queryset(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    ).prefetch_related("lines")

    cards = {
        "all": 0,
        "air": 0,
        "sea": 0,
        "road": 0,
        "courier": 0,
        "other": 0,
    }

    rows = []
    total_goods_usd = ZERO
    total_transport_usd = ZERO
    rates_cache = {}
    warnings = {"skipped": [], "soft": [], "info": []}

    for imp in qs:
        # Sum line amounts in Python using the prefetch cache.
        # _sum_goods_amount() used .aggregate() which fires a separate SQL query
        # per import despite prefetch_related("lines") already loading the lines.
        # This loop uses imp.lines.all() which hits the prefetch cache instead.
        # Behaviour is identical: NULL line_amounts are excluded, zero-value lines
        # are included (matching the original .exclude(line_amount__isnull=True)).
        goods_amount = sum(
            (line.line_amount for line in imp.lines.all() if line.line_amount is not None),
            ZERO,
        )
        transport_amount = imp.transport_price or ZERO

        goods_currency = normalize_currency(imp.currency_code)
        transport_currency = normalize_currency(imp.transport_currency)

        if goods_amount <= 0:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods amount is zero or negative",
            })
            continue

        # Info: no header transport price is an expected exclusion —
        # these imports are candidates for the fallback analysis.
        if transport_amount <= 0:
            warnings["info"].append({
                "import_code": imp.import_code,
                "reason": "no header transport price — handled by fallback analysis",
            })
            continue

        if not goods_currency:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods currency missing",
            })
            continue

        if goods_currency not in SUPPORTED_CURRENCIES:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": f"goods currency '{goods_currency}' not supported",
            })
            continue

        if not transport_currency:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "transport currency missing",
            })
            continue

        if transport_currency not in SUPPORTED_CURRENCIES:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": f"transport currency '{transport_currency}' not supported",
            })
            continue

        declaration_date = imp.declaration_date
        if not declaration_date:
            continue

        if declaration_date not in rates_cache:
            try:
                rates_cache[declaration_date] = get_nbg_rates_for_date(declaration_date)
            except ExchangeRateError:
                rates_cache[declaration_date] = None

        rates = rates_cache.get(declaration_date)
        if not rates:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": f"exchange rate unavailable for {declaration_date}",
            })
            continue

        try:
            goods_usd = convert_to_usd(goods_amount, goods_currency, rates)
            transport_usd = convert_to_usd(transport_amount, transport_currency, rates)
        except ExchangeRateError:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "currency conversion failed",
            })
            continue

        if goods_usd <= 0:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods converted to zero USD",
            })
            continue

        transport_percent = (transport_usd / goods_usd) * Decimal("100")
        method = _shipping_method_key(imp)

        cards["all"] += 1
        cards[method] += 1

        total_goods_usd += goods_usd
        total_transport_usd += transport_usd

        if include_rows:
            rows.append({
                "import_code": imp.import_code,
                "vendor_name": imp.vendor_name,
                "shipping_method": imp.shipping_method,
                "declaration_c_number": imp.declaration_c_number,
                "declaration_date": imp.declaration_date,
                "goods_amount": goods_amount.quantize(TWO_PLACES),
                "goods_currency": goods_currency,
                "goods_usd": goods_usd.quantize(TWO_PLACES),
                "transport_amount": transport_amount.quantize(TWO_PLACES),
                "transport_currency": transport_currency,
                "transport_usd": transport_usd.quantize(TWO_PLACES),
                "transport_percent": transport_percent.quantize(TWO_PLACES),
            })

    overall_percent = ZERO
    if total_goods_usd > 0:
        overall_percent = (total_transport_usd / total_goods_usd) * Decimal("100")

    summary = {
        "total_goods_usd": total_goods_usd.quantize(TWO_PLACES),
        "total_transport_usd": total_transport_usd.quantize(TWO_PLACES),
        "overall_percent": overall_percent.quantize(TWO_PLACES),
    }

    result = {
        "cards": cards,
        "summary": summary,
        "warnings": warnings,
    }

    if include_rows:
        result["rows"] = rows

    return result


# ---------------------------------------------------------------------------
# Unified cost analysis
# Combines header transport price and TRANSPORTATION line items in one pass.
# Goods and line-transport share import.currency_code (strict validation).
# Header transport uses import.transport_currency (tolerant — bad currency
# contributes 0 instead of skipping the shipment).
# ---------------------------------------------------------------------------

def build_unified_cost_analysis(
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
    ).prefetch_related("lines")

    cards = {"all": 0, "air": 0, "sea": 0, "road": 0, "courier": 0, "other": 0}
    rows = []
    total_goods_usd = ZERO
    total_transport_usd = ZERO
    rates_cache = {}
    warnings = {"skipped": [], "soft": [], "info": []}

    for imp in qs:

        # ------------------------------------------------------------------
        # STRICT: line currency governs goods and TRANSPORTATION line
        # amounts. If it is missing or unsupported the shipment is skipped
        # because goods cannot be converted.
        # ------------------------------------------------------------------
        line_currency = normalize_currency(imp.currency_code)
        if not line_currency:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods/line currency missing",
            })
            continue
        if line_currency not in SUPPORTED_CURRENCIES:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": f"goods/line currency '{line_currency}' not supported",
            })
            continue

        # ------------------------------------------------------------------
        # TOLERANT: header transport currency governs only the header price.
        # If it is missing or unsupported we set header_transport_usd = 0
        # and carry on — the shipment is NOT skipped for this reason alone.
        # ------------------------------------------------------------------
        header_transport_price = imp.transport_price or ZERO
        header_transport_currency = normalize_currency(imp.transport_currency)
        header_currency_valid = (
            bool(header_transport_currency)
            and header_transport_currency in SUPPORTED_CURRENCIES
        )

        # Soft: header price exists but its currency is unusable — the header
        # contribution will be 0. The shipment is still included.
        if header_transport_price > ZERO and not header_currency_valid:
            warnings["soft"].append({
                "import_code": imp.import_code,
                "reason": "header transport currency invalid or missing — header transport contributed 0",
            })

        # Accumulate line amounts in a single pass over lines.
        total_lines_amount = ZERO
        transportation_lines_amount = ZERO

        for line in imp.lines.all():
            if not line.line_amount or line.line_amount <= ZERO:
                continue
            total_lines_amount += line.line_amount
            if (line.item_no or "").strip().upper() == TRANSPORTATION_ITEM_NO:
                transportation_lines_amount += line.line_amount

        # ------------------------------------------------------------------
        # STRICT: at least one transport source must be present.
        # If both header transport price and TRANSPORTATION lines are zero,
        # the shipment has no transport cost recorded — exclude it.
        # ------------------------------------------------------------------
        if header_transport_price <= ZERO and transportation_lines_amount <= ZERO:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "no transport cost found — neither header transport price nor TRANSPORTATION lines present",
            })
            continue

        # ------------------------------------------------------------------
        # STRICT: goods_amount must be positive. Skip immediately — do not
        # force to 0 — because a zero or negative goods value means we
        # cannot produce a meaningful cost split for this shipment.
        # ------------------------------------------------------------------
        goods_amount = total_lines_amount - transportation_lines_amount
        if goods_amount <= ZERO:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods amount zero or negative after excluding TRANSPORTATION lines",
            })
            continue

        # Fetch exchange rates for the declaration date (cached per date).
        declaration_date = imp.declaration_date
        if not declaration_date:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "declaration date missing",
            })
            continue

        if declaration_date not in rates_cache:
            try:
                rates_cache[declaration_date] = get_nbg_rates_for_date(declaration_date)
            except ExchangeRateError:
                rates_cache[declaration_date] = None

        rates = rates_cache.get(declaration_date)
        # STRICT: without rates neither goods nor any transport can be
        # converted, so the shipment is skipped.
        if not rates:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": f"exchange rate unavailable for {declaration_date}",
            })
            continue

        # ------------------------------------------------------------------
        # STRICT: goods conversion failure → skip shipment.
        # ------------------------------------------------------------------
        try:
            goods_usd = convert_to_usd(goods_amount, line_currency, rates)
        except ExchangeRateError:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods currency conversion failed",
            })
            continue

        if goods_usd <= ZERO:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "goods converted to zero USD",
            })
            continue

        # ------------------------------------------------------------------
        # STRICT for line-transport: uses the same line_currency as goods.
        # Failure here skips the shipment because we cannot split costs
        # correctly without this value.
        # ------------------------------------------------------------------
        try:
            transport_lines_usd = (
                convert_to_usd(transportation_lines_amount, line_currency, rates)
                if transportation_lines_amount > ZERO
                else ZERO
            )
        except ExchangeRateError:
            warnings["skipped"].append({
                "import_code": imp.import_code,
                "reason": "TRANSPORTATION line currency conversion failed",
            })
            continue

        # ------------------------------------------------------------------
        # TOLERANT: header transport conversion. Bad currency or conversion
        # error → contribute 0, do not skip.
        # ------------------------------------------------------------------
        header_transport_usd = ZERO
        if header_transport_price > ZERO and header_currency_valid:
            try:
                header_transport_usd = convert_to_usd(
                    header_transport_price, header_transport_currency, rates
                )
            except ExchangeRateError:
                header_transport_usd = ZERO  # tolerant: keep going
                warnings["soft"].append({
                    "import_code": imp.import_code,
                    "reason": "header transport currency conversion failed — header transport contributed 0",
                })

        transport_usd = header_transport_usd + transport_lines_usd

        # Percent is 0 when transport_usd is 0 — shipment is still included.
        transport_percent = (
            (transport_usd / goods_usd) * Decimal("100")
            if transport_usd > ZERO
            else ZERO
        )

        method = _shipping_method_key(imp)
        cards["all"] += 1
        cards[method] += 1
        total_goods_usd += goods_usd
        total_transport_usd += transport_usd

        if include_rows:
            rows.append({
                "import_code": imp.import_code,
                "vendor_name": imp.vendor_name,
                "shipping_method": imp.shipping_method,
                "declaration_c_number": imp.declaration_c_number,
                "declaration_date": imp.declaration_date,
                "goods_amount": goods_amount.quantize(TWO_PLACES),
                "goods_currency": line_currency,
                "goods_usd": goods_usd.quantize(TWO_PLACES),
                "transportation_lines_amount": transportation_lines_amount.quantize(TWO_PLACES),
                "header_transport_amount": header_transport_price.quantize(TWO_PLACES),
                "header_transport_currency": header_transport_currency,
                "transport_usd": transport_usd.quantize(TWO_PLACES),
                "transport_percent": transport_percent.quantize(TWO_PLACES),
            })

    overall_percent = ZERO
    if total_goods_usd > ZERO:
        overall_percent = (total_transport_usd / total_goods_usd) * Decimal("100")

    result = {
        "cards": cards,
        "summary": {
            "total_goods_usd": total_goods_usd.quantize(TWO_PLACES),
            "total_transport_usd": total_transport_usd.quantize(TWO_PLACES),
            "overall_percent": overall_percent.quantize(TWO_PLACES),
        },
        "warnings": warnings,
    }

    if include_rows:
        result["rows"] = rows

    return result