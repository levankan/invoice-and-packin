from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import requests


class ExchangeRateError(Exception):
    pass


def _format_nbg_date(dt: date) -> str:
    # NBG JSON endpoint expects YYYY-MM-DD
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
    """
    date_str = _format_nbg_date(dt)
    url = f"https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date={date_str}"

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise ExchangeRateError(f"Could not fetch NBG rates for {dt}: {exc}")

    if not data or not isinstance(data, list):
        raise ExchangeRateError(f"Unexpected NBG response for {dt}")

    first = data[0]
    currencies = first.get("currencies", [])
    if not currencies:
        raise ExchangeRateError(f"No currency data returned for {dt}")

    rates: dict[str, Decimal] = {"GEL": Decimal("1")}

    for item in currencies:
        code = str(item.get("code", "")).upper().strip()
        rate = _safe_decimal(item.get("rate"))
        quantity = _safe_decimal(item.get("quantity", 1))

        if code and quantity > 0:
            rates[code] = rate / quantity

    return rates


def convert_to_usd(amount: Decimal, currency_code: str, rates: dict[str, Decimal]) -> Decimal:
    """
    rates are GEL per 1 unit of currency.
    Convert any supported currency to USD using GEL as bridge.
    """
    currency = (currency_code or "").upper().strip()

    if amount is None:
        return Decimal("0")

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