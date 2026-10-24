"""Create a source-backed figure from captured input snapshots, never synthetic fixtures."""

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from peru_macro.contracts import catalog, normalize

root = Path("data/real_inputs")
rows = {}
for spec in catalog():
    payload = json.loads((root / f"{spec['code']}.json").read_text())
    values = normalize(payload, spec, date(2005, 1, 1), date(2025, 12, 31), quarantine=True)
    monthly = {}
    for row in values:
        if row.value is not None and not row.rejection_reason:
            monthly[row.period.replace(day=1)] = float(row.value)
    rows[spec["code"]] = monthly
fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
fig.patch.set_facecolor("#f5f8fc")
for ax in axes:
    ax.set_facecolor("#f5f8fc")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.15)
for code, label, color in [
    ("PN01273PM", "Inflation, year-on-year", "#d57b35"),
    ("PD12301MD", "Policy rate, last available within month", "#126782"),
]:
    axes[0].plot(
        list(rows[code]), list(rows[code].values()), label=label, color=color, linewidth=1.6
    )
axes[0].set_title("Peru macroeconomic observations · 2005–2025", loc="left", fontweight="bold")
axes[0].set_ylabel("Percent")
axes[0].legend(frameon=False, fontsize=9)
axes[1].plot(
    list(rows["PN01207PM"]), list(rows["PN01207PM"].values()), color="#126782", linewidth=1.6
)
axes[1].set_ylabel("PEN per USD")
axes[1].set_title("Interbank exchange rate · monthly average", loc="left", fontsize=11)
fig.text(
    0.08,
    0.02,
    "Source: BCRP API snapshots · Descriptive observed values · Missing data are not forward-filled",
    fontsize=9,
    color="#526171",
)
fig.tight_layout(rect=(0, 0.04, 1, 1))
Path("docs/assets").mkdir(exist_ok=True)
fig.savefig("docs/assets/peru-macro-2005-2025.png", dpi=150)
