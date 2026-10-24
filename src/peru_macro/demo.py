"""Two synthetic vintages demonstrate correction and explicit missingness."""

import json
from pathlib import Path

from .contracts import catalog


def create_demo(folder: Path, revised: bool = False) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for spec in catalog():
        daily = spec["frequency"] == "D"
        periods = [
            {"name": "02.Jan.24" if daily else "Jan.2024", "values": ["3.25" if daily else "100"]},
            {"name": "31.Jan.24" if daily else "Feb.2024", "values": ["3.50" if daily else "101"]},
        ]
        if revised and spec["code"] == "PN01770AM":
            periods[0]["values"] = ["100.5"]
        payload = {
            "config": {"series": [{"name": "SYNTHETIC " + spec["name"]}]},
            "periods": periods,
        }
        (folder / f"{spec['code']}.json").write_text(json.dumps(payload), encoding="utf-8")
