"""Stable booking/search URL builders used by ResiFly collectors."""

from datetime import date, datetime
import re
from typing import Union
from urllib.parse import urlencode


_IATA_CODE = re.compile(r"^[A-Z]{3}$")


def _iata(value: str) -> str:
    code = value.strip().upper()
    if not _IATA_CODE.fullmatch(code):
        raise ValueError(f"Invalid IATA airport code: {value!r}")
    return code


DateValue = Union[str, date, datetime]


def _departure_date(value: DateValue) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    raw = value.strip()
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid departure date: {value!r}") from error


def wizz_booking_url(
    origin: str,
    destination: str,
    departure: DateValue,
    *,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    locale: str = "en-gb",
) -> str:
    """Return a reusable Wizz Air search link for one outbound journey.

    Wizz Air's URL encodes the route, departure date and passenger counts. It
    intentionally contains no browser-session identifier. The URL opens the
    flights available for that route and date; it does not encode a flight
    number.
    """

    passenger_counts = (adults, children, infants)
    if any(not isinstance(count, int) or count < 0 for count in passenger_counts):
        raise ValueError("Passenger counts must be non-negative integers")
    if adults < 1:
        raise ValueError("At least one adult passenger is required")

    language = locale.strip().lower()
    if not re.fullmatch(r"[a-z]{2}-[a-z]{2}", language):
        raise ValueError(f"Invalid locale: {locale!r}")

    return (
        f"https://www.wizzair.com/{language}/booking/select-flight/"
        f"{_iata(origin)}/{_iata(destination)}/{_departure_date(departure)}/"
        f"null/{adults}/{children}/{infants}/null"
    )


def ryanair_booking_url(
    origin: str,
    destination: str,
    departure: DateValue,
    *,
    adults: int = 1,
    teens: int = 0,
    children: int = 0,
    infants: int = 0,
    locale: str = "pl/pl",
) -> str:
    """Return a reusable Ryanair Fare Finder link for one outbound journey.

    Ryanair's direct ``trip/flights/select`` URL can get stuck on an empty
    availability view even when Fare Finder still publishes the route and
    fare.  Fare Finder is therefore the more useful public entry point: it
    opens the requested route and date without relying on browser-session
    state, cookies, or temporary identifiers.
    """

    passenger_counts = (adults, teens, children, infants)
    if any(not isinstance(count, int) or count < 0 for count in passenger_counts):
        raise ValueError("Passenger counts must be non-negative integers")
    if adults < 1:
        raise ValueError("At least one adult passenger is required")

    language = locale.strip().lower()
    if not re.fullmatch(r"[a-z]{2}/[a-z]{2}", language):
        raise ValueError(f"Invalid locale: {locale!r}")

    query = urlencode({
        "originIata": _iata(origin),
        "destinationIata": _iata(destination),
        "dateOut": _departure_date(departure),
        "dateIn": "",
        "isExactDate": "true",
        "outboundFromHour": "00:00",
        "outboundToHour": "23:59",
        "priceValueTo": "",
        "currency": "PLN",
        "isReturn": "false",
        "isMacDestination": "false",
        "promoCode": "",
        "adults": adults,
        "teens": teens,
        "children": children,
        "infants": infants,
    })
    return f"https://www.ryanair.com/{language}/fare-finder?{query}"

