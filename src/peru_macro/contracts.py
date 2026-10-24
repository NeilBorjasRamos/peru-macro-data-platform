"""Explicit period, value and shape contracts for one-series BCRP responses."""

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from importlib.resources import files

MONTHS = {
    name: i + 1
    for i, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}
MONTHS.update({"ene": 1, "abr": 4, "ago": 8, "set": 9, "dic": 12})
MISSING = {"", "n.d.", "n.d", "nd", "n/a", "na", "null", "-"}


@dataclass(frozen=True)
class Observation:
    code: str
    period: date
    value: Decimal | None
    rejection_reason: str | None = None
    raw_value: str | None = None


def catalog() -> list[dict]:
    return json.loads(files("peru_macro").joinpath("catalog.json").read_text())


def parse_period(text: str, frequency: str) -> date:
    if frequency == "M":
        match = re.fullmatch(r"([A-Za-z]{3})\.(\d{4})", text)
        if not match:
            raise ValueError(f"Unexpected monthly period: {text!r}")
        month, year = match.groups()
        return date(int(year), MONTHS[month.lower()], 1)
    if frequency == "D":
        match = re.fullmatch(r"(\d{2})\.([A-Za-z]{3})\.(\d{2})", text)
        if not match:
            raise ValueError(f"Unexpected daily period: {text!r}")
        day, month, year = match.groups()
        # This project deliberately limits daily retrieval to 2000–2099.
        return date(2000 + int(year), MONTHS[month.lower()], int(day))
    raise ValueError("Only M and D frequencies are supported")


def parse_value(raw) -> Decimal | None:
    if raw is None or (isinstance(raw, str) and raw.strip().lower() in MISSING):
        return None
    if not isinstance(raw, (str, int, float)) or isinstance(raw, bool):
        raise ValueError("Observation value must be numeric text or a missing marker")
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric observation: {raw!r}") from exc
    if not value.is_finite() or abs(value) >= Decimal("1e100"):
        raise ValueError("Nonfinite or out-of-contract numeric observation")
    return value


def normalize(
    payload: dict, spec: dict, start: date, end: date, quarantine: bool = False
) -> list[Observation]:
    series = payload.get("config", {}).get("series", [])
    periods = payload.get("periods")
    if len(series) != 1 or not isinstance(series[0].get("name"), str):
        raise ValueError("Expected exactly one named source series")
    if not isinstance(periods, list) or not periods:
        raise ValueError(f"No source periods for {spec['code']}")
    rows = []
    seen = set()
    for period in periods:
        values = period.get("values")
        if not isinstance(values, list) or len(values) != 1:
            raise ValueError("Expected one value per requested series")
        try:
            day = parse_period(period["name"], spec["frequency"])
        except (KeyError, TypeError) as exc:
            raise ValueError("Unknown source period label") from exc
        if not start <= day <= end:
            raise ValueError("Source period is outside the request")
        if day in seen:
            raise ValueError("Duplicate business key in source snapshot")
        seen.add(day)
        try:
            value = parse_value(values[0])
            rows.append(Observation(spec["code"], day, value))
        except ValueError:
            if not quarantine:
                raise
            rows.append(Observation(spec["code"], day, None, "invalid_numeric", str(values[0])))
    if not any(row.value is not None for row in rows):
        raise ValueError("All source observations are missing")
    return sorted(rows, key=lambda row: row.period)
