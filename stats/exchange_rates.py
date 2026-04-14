from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import requests
from django.core.cache import cache


class ExchangeRateError(Exception):
    pass


def _format_nbg_date(dt: date) -> str:
    return dt.strftime("%Y-%m-%d")


def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, TypeError):
        raise ExchangeRateError(f"Invalid decimal value: {value}")


def fetch_nbg_rates_for_date(dt: date) -> dict[str, Decimal]:
    """
    Returns GEL-per-1-unit-of-currency for the given date.
    Example:
        USD -> 2.7231
        EUR -> 3.1471
        GEL -> 1

    Safe behavior:
    - short timeout
    - catches request errors
    - validates response structure
    - raises ExchangeRateError with readable message
    """
    if not dt:
        raise ExchangeRateError("Date is required for NBG exchange rate lookup")

    date_str = _format_nbg_date(dt)
    url = f"https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date={date_str}"

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise ExchangeRateError(f"NBG request timed out for {dt}") from exc
    except requests.exceptions.ConnectionError as exc:
        raise ExchangeRateError(f"Could not connect to NBG for {dt}") from exc
    except requests.exceptions.HTTPError as exc:
        raise ExchangeRateError(f"NBG returned HTTP error for {dt}: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise ExchangeRateError(f"Could not fetch NBG rates for {dt}: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise ExchangeRateError(f"Invalid JSON received from NBG for {dt}") from exc

    if not data or not isinstance(data, list):
        raise ExchangeRateError(f"Unexpected NBG response for {dt}")

    first = data[0]
    if not isinstance(first, dict):
        raise ExchangeRateError(f"Unexpected NBG payload structure for {dt}")

    currencies = first.get("currencies", [])
    if not isinstance(currencies, list) or not currencies:
        raise ExchangeRateError(f"No currency data returned for {dt}")

    rates: dict[str, Decimal] = {"GEL": Decimal("1")}

    for item in currencies:
        if not isinstance(item, dict):
            continue

        code = str(item.get("code", "")).upper().strip()
        if not code:
            continue

        try:
            rate = _safe_decimal(item.get("rate"))
            quantity = _safe_decimal(item.get("quantity", 1))
        except ExchangeRateError:
            continue

        if quantity > 0:
            rates[code] = rate / quantity

    if "USD" not in rates:
        raise ExchangeRateError(f"USD rate missing in NBG response for {dt}")

    return rates


def get_nbg_rates_for_date(dt: date) -> dict[str, Decimal]:
    """
    Cached wrapper around fetch_nbg_rates_for_date.

    Exchange rates for a given date are historical and never change,
    so a 24-hour TTL is safe. The raw fetcher is left untouched.
    """
    if not dt:
        raise ExchangeRateError("Date is required for NBG exchange rate lookup")

    cache_key = f"nbg_rates_{dt.strftime('%Y-%m-%d')}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    rates = fetch_nbg_rates_for_date(dt)
    cache.set(cache_key, rates, timeout=86400)  # 24 hours
    return rates


def convert_to_usd(amount: Decimal, currency_code: str, rates: dict[str, Decimal]) -> Decimal:
    """
    rates are GEL per 1 unit of currency.
    Convert any supported currency to USD using GEL as bridge.
    """
    currency = (currency_code or "").upper().strip()

    if amount is None:
        return Decimal("0")

    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ExchangeRateError(f"Invalid amount: {amount}") from exc

    if currency == "USD":
        return amount

    usd_rate = rates.get("USD")
    if not usd_rate or usd_rate == 0:
        raise ExchangeRateError("USD rate missing")

    if currency == "GEL":
        return amount / usd_rate

    src_rate = rates.get(currency)
    if not src_rate:
        raise ExchangeRateError(f"Rate not found for currency: {currency}")

    gel_amount = amount * src_rate
    return gel_amount / usd_rate