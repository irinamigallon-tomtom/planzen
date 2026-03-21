"""
Pure business logic for planzen — no file I/O allowed here.

Transforms parsed plan data into the weekly-allocation output table
described in LOGIC.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from planzen.config import (
    ABSENCE_PW_PER_PERSON,
    COL_BUDGET_BUCKET,
    COL_EPIC,
    COL_ESTIMATION,
    COL_PRIORITY,
    LABEL_ENG_ABSENCE,
    LABEL_ENG_BRUTO,
    LABEL_ENG_NET,
    LABEL_MGMT_ABSENCE,
    LABEL_MGMT_CAPACITY,
    LABEL_MGMT_NET,
    LABEL_TOTAL_BUCKET,
    LABEL_TOTAL_ROW,
    OUT_COL_BUDGET_BUCKET,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_PRIORITY,
    OUT_COL_TOTAL_WEEKS,
)


@dataclass
class CapacityConfig:
    """
    Weekly capacity derived from head counts, in Person-Weeks (PW).

    Each person contributes 1 PW of bruto capacity per week.
    Absence is assumed to be 1/12 of bruto for both engineers and managers.
    Net capacity = bruto − absence.
    """

    num_engineers: int
    num_managers: int

    @property
    def eng_bruto(self) -> float:
        return float(self.num_engineers)

    @property
    def eng_absence(self) -> float:
        return round(self.num_engineers * ABSENCE_PW_PER_PERSON, 1)

    @property
    def eng_net(self) -> float:
        return round(self.eng_bruto - self.eng_absence, 1)

    @property
    def mgmt_capacity(self) -> float:
        return float(self.num_managers)

    @property
    def mgmt_absence(self) -> float:
        return round(self.num_managers * ABSENCE_PW_PER_PERSON, 1)

    @property
    def mgmt_net(self) -> float:
        return round(self.mgmt_capacity - self.mgmt_absence, 1)


def _mondays_in_range(start: date, end: date) -> list[date]:
    """Return all Mondays (inclusive) between start and end."""
    mondays: list[date] = []
    day = start
    # advance to first Monday
    day += timedelta(days=(7 - day.weekday()) % 7)
    while day <= end:
        mondays.append(day)
        day += timedelta(weeks=1)
    return mondays


def build_output_table(
    epics_df: pd.DataFrame,
    capacity: CapacityConfig,
    start: date,
    end: date,
) -> pd.DataFrame:
    """
    Build the output allocation table from the parsed epics DataFrame.

    Parameters
    ----------
    epics_df:
        DataFrame with columns: Epics, Estimation, Budget Bucket, Priority, Milestone.
    capacity:
        Weekly capacity values (bruto, absence, management).
    start / end:
        Date range; week columns are generated for every Monday in [start, end].

    Returns
    -------
    DataFrame matching the structure described in LOGIC.md.
    """
    mondays = _mondays_in_range(start, end)
    week_labels = [d.strftime("%-m.%d").lstrip("0") or "0" for d in mondays]

    # --- capacity header rows ---
    capacity_rows = _build_capacity_rows(capacity, week_labels)

    # --- epic rows with evenly distributed allocation ---
    epic_rows = _allocate_epics(epics_df, capacity, mondays, week_labels)

    # --- total / weekly allocation row ---
    total_row = _build_total_row(epic_rows, week_labels)

    rows = capacity_rows + epic_rows + [total_row]
    columns = [
        OUT_COL_BUDGET_BUCKET,
        OUT_COL_EPIC,
        OUT_COL_PRIORITY,
        OUT_COL_ESTIMATION,
        OUT_COL_TOTAL_WEEKS,
        *week_labels,
    ]
    return pd.DataFrame(rows, columns=columns)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_capacity_rows(
    capacity: CapacityConfig, week_labels: list[str]
) -> list[dict]:
    def _row(label: str, value: float) -> dict:
        base: dict = {
            OUT_COL_BUDGET_BUCKET: "",
            OUT_COL_EPIC: label,
            OUT_COL_PRIORITY: "",
            OUT_COL_ESTIMATION: "",
            OUT_COL_TOTAL_WEEKS: "",
        }
        base.update({w: value for w in week_labels})
        return base

    return [
        _row(LABEL_ENG_BRUTO, capacity.eng_bruto),
        _row(LABEL_ENG_ABSENCE, capacity.eng_absence),
        _row(LABEL_ENG_NET, capacity.eng_net),
        _row(LABEL_MGMT_CAPACITY, capacity.mgmt_capacity),
        _row(LABEL_MGMT_ABSENCE, capacity.mgmt_absence),
        _row(LABEL_MGMT_NET, capacity.mgmt_net),
    ]


def _allocate_epics(
    epics_df: pd.DataFrame,
    capacity: CapacityConfig,
    mondays: list[date],
    week_labels: list[str],
) -> list[dict]:
    """
    Distribute each Epic's Estimation evenly across weeks, capped so that:
    - per-Epic sum ≤ Estimation
    - per-week sum across all Epics ≤ Engineering Net Capacity
    """
    n_weeks = len(mondays)
    rows: list[dict] = []

    # Track remaining net capacity per week
    remaining: list[float] = [capacity.eng_net] * n_weeks

    for _, epic in epics_df.iterrows():
        estimation = float(epic[COL_ESTIMATION])
        weekly_ideal = round(estimation / n_weeks, 1) if n_weeks else 0.0

        allocations: list[float] = []
        total_allocated = 0.0

        for i in range(n_weeks):
            budget_left = round(estimation - total_allocated, 1)
            alloc = min(weekly_ideal, remaining[i], budget_left)
            alloc = round(alloc, 1)
            allocations.append(alloc)
            remaining[i] = round(remaining[i] - alloc, 1)
            total_allocated = round(total_allocated + alloc, 1)

        total_weeks = round(sum(allocations), 1)
        row: dict = {
            OUT_COL_BUDGET_BUCKET: epic[COL_BUDGET_BUCKET],
            OUT_COL_EPIC: epic[COL_EPIC],
            OUT_COL_PRIORITY: epic.get(COL_PRIORITY, ""),
            OUT_COL_ESTIMATION: estimation,
            OUT_COL_TOTAL_WEEKS: total_weeks,
        }
        row.update(dict(zip(week_labels, allocations)))
        rows.append(row)

    return rows


def _build_total_row(epic_rows: list[dict], week_labels: list[str]) -> dict:
    row: dict = {
        OUT_COL_BUDGET_BUCKET: LABEL_TOTAL_BUCKET,
        OUT_COL_EPIC: LABEL_TOTAL_ROW,
        OUT_COL_PRIORITY: "",
        OUT_COL_ESTIMATION: "",
        OUT_COL_TOTAL_WEEKS: "",
    }
    for w in week_labels:
        row[w] = round(sum(r[w] for r in epic_rows), 1)
    return row
