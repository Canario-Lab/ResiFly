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
    """Return a reusable Ryanair search link for one outbound journey."""

    passenger_counts = (adults, teens, children, infants)
    if any(not isinstance(count, int) or count < 0 for count in passenger_counts):
        raise ValueError("Passenger counts must be non-negative integers")
    if adults < 1:
        raise ValueError("At least one adult passenger is required")

    language = locale.strip().lower()
    if not re.fullmatch(r"[a-z]{2}/[a-z]{2}", language):
        raise ValueError(f"Invalid locale: {locale!r}")

    query = urlencode({
        "adults": adults,
        "teens": teens,
        "children": children,
        "infants": infants,
        "dateOut": _departure_date(departure),
        "dateIn": "",
        "isConnectedFlight": "false",
        "discount": 0,
        "promoCode": "",
        "isReturn": "false",
        "originIata": _iata(origin),
        "destinationIata": _iata(destination),
        "tpAdults": adults,
        "tpTeens": teens,
        "tpChildren": children,
        "tpInfants": infants,
    })
    return f"https://www.ryanair.com/{language}/trip/flights/select?{query}"


def iberia_booking_url(
    origin: str,
    destination: str,
    departure: DateValue,
    *,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    resident_code: str = "RC",
) -> str:
    """Return a reusable Iberia search link for one outbound journey.

    ``RC`` is Iberia's public search code for a Canary Islands resident. The
    URL contains search inputs only; no browser-session data is persisted.
    """

    passenger_counts = (adults, children, infants)
    if any(not isinstance(count, int) or count < 0 for count in passenger_counts):
        raise ValueError("Passenger counts must be non-negative integers")
    if adults < 1:
        raise ValueError("At least one adult passenger is required")

    departure_day = date.fromisoformat(_departure_date(departure))
    query = urlencode({
        "market": "ES",
        "language": "es",
        "appliesOMB": "false",
        "splitEndCity": "false",
        "initializedOMB": "true",
        "flexible": "false",
        "TRIP_TYPE": 1,
        "BEGIN_CITY_01": _iata(origin),
        "END_CITY_01": _iata(destination),
        "BEGIN_DAY_01": f"{departure_day.day:02d}",
        "BEGIN_MONTH_01": departure_day.strftime("%Y%m"),
        "BEGIN_YEAR_01": departure_day.year,
        "FARE_TYPE": "R",
        "ADT": adults,
        "CHD": children,
        "INF": infants,
        "BNN": 0,
        "YTH": 0,
        "YCD": 0,
        "residentCode": resident_code.strip().upper(),
        "familianumerosa": "",
        "bookingMarket": "ES",
    })
    return f"https://www.iberia.com/flights/?{query}#!/availability"


def vueling_booking_url(
    origin: str,
    destination: str,
    departure: DateValue,
    *,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    resident_discount: bool = True,
    locale: str = "es-ES",
    currency: str = "EUR",
) -> str:
    """Return Vueling's documented, reusable one-way booking deeplink.

    Vueling documents ``dt=1`` as the island/Ceuta resident discount.  The
    basic deeplink deliberately contains only route, date, passenger and
    locale data; it has no session token and does not pretend to preselect a
    fare basis that the collector did not receive from Vueling.
    """

    passenger_counts = (adults, children, infants)
    if any(not isinstance(count, int) or count < 0 for count in passenger_counts):
        raise ValueError("Passenger counts must be non-negative integers")
    if adults < 1:
        raise ValueError("At least one adult passenger is required")

    culture = locale.strip()
    if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", culture):
        raise ValueError(f"Invalid locale: {locale!r}")
    currency_code = currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency_code):
        raise ValueError(f"Invalid currency: {currency!r}")

    query = urlencode({
        "o": _iata(origin),
        "d": _iata(destination),
        "dd": _departure_date(departure),
        "dt": 1 if resident_discount else 0,
        "adt": adults,
        "chd": children,
        "inf": infants,
        "c": culture,
        "cur": currency_code,
    })
    return f"https://tickets.vueling.com/booking?{query}"


def air_europa_booking_url(
    origin: str,
    destination: str,
    departure: DateValue,
    *,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
) -> str:
    """Return Air Europa's official, reusable one-way deeplink.

    The parameters match the URL returned by Air Europa's branded deeplink
    service.  The link contains route, date and passenger counts only; it has
    no cookies, API keys or browser-session identifiers.  Air Europa asks the
    customer to confirm resident eligibility during purchase.
    """

    passenger_counts = (adults, children, infants)
    if any(not isinstance(count, int) or count < 0 for count in passenger_counts):
        raise ValueError("Passenger counts must be non-negative integers")
    if adults < 1:
        raise ValueError("At least one adult passenger is required")

    compact_date = date.fromisoformat(_departure_date(departure)).strftime("%Y%m%d")
    query = urlencode({
        "departure_airport": _iata(origin),
        "arrival_airport": _iata(destination),
        "departure_date": compact_date,
        "adults": adults,
        "children": children,
        "infants": infants,
        "channel": "trfx",
        "trip_type": "O",
        "config_ext": "int",
    })
    return f"https://www.aireuropa.com/es/es/deeplink?{query}"

