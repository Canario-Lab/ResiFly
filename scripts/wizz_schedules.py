"""Read verified Wizz schedules without importing any collector."""

import json
from datetime import date
from pathlib import Path


WIZZ_ROUTE_FILE = Path(__file__).resolve().parents[1] / "data" / "wizz-route-schedules.json"


class ScheduleOverrides(dict):
    def __init__(self):
        super().__init__()
        self.durations = {}
        self.weekdays = {}
        self.dates = {}


def read_overrides(rows, schedules, weekday_rows=(), dated_rows=()):
    overrides = ScheduleOverrides()
    for item in rows:
        key = (item["origin"], item["destination"], item["departure_time"])
        if key in overrides or key[:2] not in schedules:
            raise RuntimeError(f"Duplicate or unregistered Wizz override: {key}")
        overrides[key] = item["flight_number"]
        if "duration_minutes" in item:
            duration = int(item["duration_minutes"])
            if duration <= 0:
                raise RuntimeError(f"Invalid Wizz override duration: {key}")
            overrides.durations[key] = duration
    for rows, field, target in ((weekday_rows, "departure_weekday", overrides.weekdays),
                                (dated_rows, "departure_date", overrides.dates)):
        for item in rows:
            value = item[field]
            if field == "departure_weekday":
                if type(value) is not int or not 1 <= value <= 7:
                    raise RuntimeError("Invalid Wizz departure weekday")
            else:
                date.fromisoformat(value)
            key = (item["origin"], item["destination"], item["departure_time"], value)
            duration = int(item["duration_minutes"])
            if key[:2] not in schedules or key in target or duration <= 0:
                raise RuntimeError(f"Duplicate or invalid Wizz calendar override: {key}")
            target[key] = (item["flight_number"], duration)
    return overrides


def resolve_schedule(schedules, overrides, origin, destination, departure):
    try:
        number, duration = schedules[(origin, destination)]
    except KeyError as error:
        raise RuntimeError(f"Active Wizz route {origin}-{destination} needs verified schedule metadata") from error
    key = (origin, destination, departure.strftime("%H:%M"))
    result = overrides.get(key, number), getattr(overrides, "durations", {}).get(key, duration)
    result = getattr(overrides, "weekdays", {}).get((*key, departure.isoweekday()), result)
    return getattr(overrides, "dates", {}).get((*key, departure.date().isoformat()), result)


def load_wizz_route_data(path: Path = WIZZ_ROUTE_FILE):
    document = json.loads(path.read_text(encoding="utf-8"))
    schedules = {}
    for route in document["routes"]:
        key = (route["origin"], route["destination"])
        duration = int(route["duration_minutes"])
        if key in schedules or duration <= 0:
            raise RuntimeError(f"Duplicate or invalid Wizz schedule: {key}")
        schedules[key] = (route["flight_number"], duration)
    overrides = read_overrides(document.get("flight_number_overrides_by_departure_time", []), schedules,
                               document.get("flight_number_overrides_by_departure_weekday_and_time", []),
                               document.get("flight_number_overrides_by_departure_date_and_time", []))
    return schedules, overrides
