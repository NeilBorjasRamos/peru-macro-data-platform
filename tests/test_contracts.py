from datetime import date
from decimal import Decimal

import pytest

from peru_macro.contracts import catalog, normalize, parse_period, parse_value
from peru_macro.demo import create_demo

SPEC = catalog()[0]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.00", Decimal("1")),
        ("-0.12", Decimal("-0.12")),
        ("n.d.", None),
        (None, None),
        ("", None),
        ("0", Decimal(0)),
        ("0.0192113272793558", Decimal("0.0192113272793558")),
    ],
)
def test_values(raw, expected):
    assert parse_value(raw) == expected


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "bad", True, [], {}, "1e101"])
def test_bad_values(raw):
    with pytest.raises(ValueError):
        parse_value(raw)


@pytest.mark.parametrize(
    "text,freq,expected",
    [
        ("Jan.2024", "M", date(2024, 1, 1)),
        ("Dec.2025", "M", date(2025, 12, 1)),
        ("29.Feb.24", "D", date(2024, 2, 29)),
    ],
)
def test_period(text, freq, expected):
    assert parse_period(text, freq) == expected


def payload(periods):
    return {"config": {"series": [{"name": "test"}]}, "periods": periods}


def test_duplicate_period_fails():
    item = {"name": "Jan.2024", "values": ["10"]}
    with pytest.raises(ValueError, match="Duplicate"):
        normalize(payload([item, item]), SPEC, date(2024, 1, 1), date(2024, 12, 31))


@pytest.mark.parametrize(
    "body",
    [
        {},
        payload([]),
        payload([{"name": "Jan.2024", "values": []}]),
        payload([{"name": "Jan.2024", "values": ["n.d."]}]),
        payload([{"name": "Jan.2023", "values": ["1"]}]),
    ],
)
def test_shape_and_range(body):
    with pytest.raises(ValueError):
        normalize(body, SPEC, date(2024, 1, 1), date(2024, 12, 31))


def test_demo_is_explicit_and_revises_one_series(tmp_path):
    import json

    create_demo(tmp_path)
    before = {p.name: p.read_text() for p in tmp_path.glob("*.json")}
    create_demo(tmp_path, revised=True)
    changed = [p.name for p in tmp_path.glob("*.json") if p.read_text() != before[p.name]]
    assert changed == ["PN01770AM.json"]
    assert all(
        "SYNTHETIC" in json.loads(p.read_text())["config"]["series"][0]["name"]
        for p in tmp_path.glob("*.json")
    )


def test_english_api_daily_september_alias():
    assert parse_period("14.Set.17", "D") == date(2017, 9, 14)


def test_invalid_numeric_can_be_quarantined_without_correction():
    rows = normalize(
        payload(
            [
                {"name": "Jan.2024", "values": ["100"]},
                {"name": "Feb.2024", "values": ["3.7512301,2011-04-07,3.75"]},
            ]
        ),
        SPEC,
        date(2024, 1, 1),
        date(2024, 12, 31),
        quarantine=True,
    )
    assert rows[1].value is None
    assert rows[1].rejection_reason == "invalid_numeric"
    assert rows[1].raw_value == "3.7512301,2011-04-07,3.75"
