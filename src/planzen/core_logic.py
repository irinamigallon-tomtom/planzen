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
    FISCAL_QUARTERS,
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

_NON_EPIC_LABELS = frozenset({
    LABEL_ENG_BRUTO, LABEL_ENG_ABSENCE, LABEL_ENG_NET,
    LABEL_MGMT_CAPACITY, LABEL_MGMT_ABSENCE, LABEL_MGMT_NET,
    LABEL_TOTAL_ROW,
})


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


def get_quarter_dates(quarter: int) -> tuple[date, date]:
    """
    Return (start_monday, end_monday) for the given fiscal quarter (1–4).

    Raises ValueError for quarters outside 1–4.
    """
    if quarter not in FISCAL_QUARTERS:
        raise ValueError(
            f"Quarter must be 1–4, got {quarter!r}. "
            f"Valid quarters: {sorted(FISCAL_QUARTERS)}"
        )
    return FISCAL_QUARTERS[quarter]


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


def validate_allocation(
    output_df: pd.DataFrame,
    capacity: CapacityConfig,
) -> list[str]:
    """
    Check mandatory constraints on the output allocation table.

    Returns a list of violation messages; empty list means all checks pass.

    Checks:
    1. Per-epic total allocated PW ≤ Estimation.
    2. Per-week sum across all epics ≤ Engineer Net Capacity.
    """
    non_week = {
        OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
        OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS,
    }
    week_cols = [c for c in output_df.columns if c not in non_week]
    epic_rows = output_df[~output_df[OUT_COL_EPIC].isin(_NON_EPIC_LABELS)]

    violations: list[str] = []

    for _, row in epic_rows.iterrows():
        estimation = float(row[OUT_COL_ESTIMATION])
        total = round(sum(float(row[w]) for w in week_cols), 10)
        if total > estimation + 1e-9:
            violations.append(
                f"Epic '{row[OUT_COL_EPIC]}': allocated {total:.1f} PW "
                f"exceeds estimation {estimation:.1f} PW"
            )

    for w in week_cols:
        week_sum = round(sum(float(v) for v in epic_rows[w]), 10)
        if week_sum > capacity.eng_net + 1e-9:
            violations.append(
                f"Week '{w}': total {week_sum:.1f} PW exceeds "
                f"Engineer Net Capacity {capacity.eng_net:.1f} PW"
            )

    return violations


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
    week_labels = [d.strftime("%b.%d") for d in mondays]

    # --- capacity header rows ---
    capacity_rows = _build_capacity_rows(capacity, week_labels)

    # --- epic rows with evenly distributed allocation ---
    epic_rows = _allocate_epics(epics_df, capacity, mondays, week_labels)

    # --- sanity-check the allocator output (violations indicate a logic bug) ---
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
    result = pd.DataFrame(rows, columns=columns)

    violations = validate_allocation(result, capacity)
    if violations:
        details = "\n  ".join(violations)
        raise RuntimeError(
            f"Allocation produced constraint violations (this is a bug):\n  {details}"
        )

    return result


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
    Distribute each Epic's Estimation across weeks, sorted by Priority so that
    higher-priority epics (lower number) claim capacity first.

    Allocation rules:
    - Per-epic sum ≤ Estimation.
    - Per-week sum across all epics ≤ Engineer Net Capacity.
    - Sequential: once an epic starts, every week with available capacity must
      also receive allocation (≥ 0.1 PW), until the budget is exhausted.
    - A week gets 0 for an epic only when that week's remaining capacity is
      fully consumed by higher-priority epics.
    """
    n_weeks = len(mondays)
    rows: list[dict] = []

    # Higher-priority epics (lower Priority number) allocate first.
    sorted_epics = epics_df.sort_values(COL_PRIORITY, kind="stable")

    # Track remaining net capacity per week across all epics.
    remaining: list[float] = [capacity.eng_net] * n_weeks

    for _, epic in sorted_epics.iterrows():
        estimation = float(epic[COL_ESTIMATION])
        # Minimum weekly unit is 0.1 PW; prevent rounding tiny estimations to 0.
        weekly_ideal = max(round(estimation / n_weeks, 1), 0.1) if estimation > 0 else 0.0

        allocations: list[float] = []
        total_allocated = 0.0

        for i in range(n_weeks):
            budget_left = round(estimation - total_allocated, 1)
            if budget_left <= 1e-9 or remaining[i] <= 1e-9:
                alloc = 0.0
            else:
                # Allocate weekly_ideal, but at least 0.1 to preserve sequential continuity.
                alloc = round(min(weekly_ideal, remaining[i], budget_left), 1)
                if alloc < 0.1:
                    alloc = round(min(0.1, remaining[i], budget_left), 1)

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
