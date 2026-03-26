"""
Pure business logic for planzen — no file I/O allowed here.

Transforms parsed plan data into the weekly-allocation output table
described in LOGIC.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from planzen.config import (
    ABSENCE_PW_PER_PERSON,
    ALLOC_MODE_DEFAULT,
    ALLOC_MODE_GAPS,
    ALLOC_MODE_UNIFORM,
    COL_ALLOC_MODE,
    COL_BUDGET_BUCKET,
    COL_DEPENDS_ON,
    COL_EPIC,
    COL_ESTIMATION,
    COL_PRIORITY,
    FISCAL_QUARTERS,
    LABEL_CAPACITY_ALERT_ROW,
    LABEL_ENG_ABSENCE,
    LABEL_ENG_BRUTO,
    LABEL_ENG_NET,
    LABEL_MGMT_ABSENCE,
    LABEL_MGMT_CAPACITY,
    LABEL_MGMT_NET,
    LABEL_TOTAL_BUCKET,
    LABEL_TOTAL_ROW,
    MAX_WEEKLY_ALLOC_PW,
    OUT_COL_BUDGET_BUCKET,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_OFF_ESTIMATE,
    OUT_COL_PRIORITY,
    OUT_COL_TOTAL_WEEKS,
    VALID_ALLOC_MODES,
)

_NON_EPIC_LABELS = frozenset({
    LABEL_ENG_BRUTO, LABEL_ENG_ABSENCE, LABEL_ENG_NET,
    LABEL_MGMT_CAPACITY, LABEL_MGMT_ABSENCE, LABEL_MGMT_NET,
    LABEL_TOTAL_ROW, LABEL_CAPACITY_ALERT_ROW,
})

_ESTIMATE_TOLERANCE_PW = 0.05


@dataclass
class CapacityConfig:
    """
    Weekly capacity configuration in Person-Weeks (PW).

    Supports two modes:

    * **Constant** — provide scalar ``num_engineers`` / ``num_managers`` and
      optional scalar absence values.  Every week gets the same capacity.
    * **Per-week** — provide ``eng_bruto_by_week`` / ``eng_absence_by_week``
      dicts keyed by Monday ``date``.  For Q weeks absent from the dict the
      scalar fallback is used (bruto) or 0 is assumed (absence).  Overflow
      weeks (beyond the primary quarter) use the scalar fallback for bruto
      and the default formula (bruto × absence rate) for absence.

    Net capacity for a given week: ``eng_bruto_for(w) − eng_absence_for(w)``.
    """

    num_engineers: float
    num_managers: float
    eng_absence_per_week: float | None = None
    mgmt_absence_per_week: float | None = None

    # Optional per-week overrides (keyed by Monday date)
    eng_bruto_by_week: dict[date, float] | None = None
    eng_absence_by_week: dict[date, float] | None = None

    # Primary quarter weeks — used to distinguish Q weeks from overflow weeks
    # when per-week absence data is provided.
    q_weeks: frozenset[date] | None = None

    # --- per-week accessor methods (used throughout allocation logic) ---

    def eng_bruto_for(self, week: date) -> float:
        if self.eng_bruto_by_week:
            return self.eng_bruto_by_week.get(week, self.num_engineers)
        return self.num_engineers

    def eng_absence_for(self, week: date) -> float:
        if self.eng_absence_by_week is not None:
            if week in self.eng_absence_by_week:
                return self.eng_absence_by_week[week]
            # Within-Q weeks not listed → 0 (lenient per-week mode).
            # Overflow weeks → default formula so capacity is realistic.
            if self.q_weeks is None or week in self.q_weeks:
                return 0.0
            return round(self.eng_bruto_for(week) * ABSENCE_PW_PER_PERSON, 1)
        if self.eng_absence_per_week is not None:
            return round(self.eng_absence_per_week, 1)
        return round(self.eng_bruto_for(week) * ABSENCE_PW_PER_PERSON, 1)

    def eng_net_for(self, week: date) -> float:
        return round(self.eng_bruto_for(week) - self.eng_absence_for(week), 1)

    # --- scalar properties (constant-mode fallbacks, used for display) ---

    @property
    def eng_bruto(self) -> float:
        return self.num_engineers

    @property
    def eng_absence(self) -> float:
        if self.eng_absence_per_week is not None:
            return round(self.eng_absence_per_week, 1)
        return round(self.num_engineers * ABSENCE_PW_PER_PERSON, 1)

    @property
    def eng_net(self) -> float:
        return round(self.eng_bruto - self.eng_absence, 1)

    @property
    def mgmt_capacity(self) -> float:
        return self.num_managers

    @property
    def mgmt_absence(self) -> float:
        if self.mgmt_absence_per_week is not None:
            return round(self.mgmt_absence_per_week, 1)
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
    mondays: list[date],
) -> list[str]:
    """
    Check mandatory constraints on the output allocation table.

    Returns a list of violation messages; empty list means all checks pass.

    Checks:
    1. Per-epic total allocated PW ≤ Estimation.
    2. Per-week sum across all epics ≤ Engineer Net Capacity for that week.
    """
    non_week = {
        OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
        OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS, OUT_COL_OFF_ESTIMATE,
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

    for w, monday in zip(week_cols, mondays):
        week_sum = round(sum(float(v) for v in epic_rows[w]), 10)
        eng_net = capacity.eng_net_for(monday)
        if week_sum > eng_net + 1e-9:
            violations.append(
                f"Week '{w}': total {week_sum:.1f} PW exceeds "
                f"Engineer Net Capacity {eng_net:.1f} PW"
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

    Overflow into the next quarter is automatic: if the total estimation
    exceeds ``capacity.eng_net × n_primary_weeks``, 13 additional Mondays
    are appended to the allocation window.

    Parameters
    ----------
    epics_df:
        DataFrame with columns: Epic Description, Estimation, Budget Bucket, Priority, …
    capacity:
        Weekly capacity values (bruto, absence, management).
    start / end:
        Primary quarter date range; one week column per Monday in [start, end].

    Returns
    -------
    DataFrame matching the structure described in LOGIC.md.
    """
    primary_mondays = _mondays_in_range(start, end)
    n_base_weeks = len(primary_mondays)

    total_estimation = float(epics_df[COL_ESTIMATION].sum())
    quarter_capacity = sum(capacity.eng_net_for(m) for m in primary_mondays)

    if total_estimation > quarter_capacity + 1e-9:
        overflow_start = end + timedelta(weeks=1)
        overflow_end = overflow_start + timedelta(weeks=12)
        mondays = primary_mondays + _mondays_in_range(overflow_start, overflow_end)
    else:
        mondays = primary_mondays

    week_labels = [d.strftime("%b.%d") for d in mondays]

    # --- capacity header rows ---
    capacity_rows = _build_capacity_rows(capacity, mondays, week_labels, n_base_weeks)

    # --- epic rows with allocation per mode ---
    epic_rows = _allocate_epics(epics_df, capacity, mondays, week_labels, n_base_weeks)

    # --- sanity-check the allocator output (violations indicate a logic bug) ---
    total_row = _build_total_row(epic_rows, week_labels)
    capacity_alert_row = _build_capacity_alert_row(total_row, capacity, mondays, week_labels)

    rows = capacity_rows + epic_rows + [total_row, capacity_alert_row]
    columns = [
        OUT_COL_BUDGET_BUCKET,
        OUT_COL_EPIC,
        OUT_COL_PRIORITY,
        OUT_COL_ESTIMATION,
        OUT_COL_TOTAL_WEEKS,
        OUT_COL_OFF_ESTIMATE,
        *week_labels,
    ]
    result = pd.DataFrame(rows, columns=columns)

    violations = validate_allocation(result, capacity, mondays)
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
    capacity: CapacityConfig, mondays: list[date], week_labels: list[str], n_base_weeks: int
) -> list[dict]:
    def _row(label: str, value_fn) -> dict:
        base: dict = {
            OUT_COL_BUDGET_BUCKET: "",
            OUT_COL_EPIC: label,
            OUT_COL_PRIORITY: "",
            OUT_COL_ESTIMATION: "",
            OUT_COL_TOTAL_WEEKS: "",
            OUT_COL_OFF_ESTIMATE: "",
        }
        week_values = {w: value_fn(m) for w, m in zip(week_labels, mondays)}
        base.update(week_values)
        # Total Weeks sums only the requested quarter (first n_base_weeks columns)
        q_values = [week_values[w] for w in week_labels[:n_base_weeks]]
        base[OUT_COL_TOTAL_WEEKS] = round(sum(q_values), 1)
        return base

    return [
        _row(LABEL_ENG_BRUTO,     capacity.eng_bruto_for),
        _row(LABEL_ENG_ABSENCE,   capacity.eng_absence_for),
        _row(LABEL_ENG_NET,       capacity.eng_net_for),
        _row(LABEL_MGMT_CAPACITY, lambda _: capacity.mgmt_capacity),
        _row(LABEL_MGMT_ABSENCE,  lambda _: capacity.mgmt_absence),
        _row(LABEL_MGMT_NET,      lambda _: capacity.mgmt_net),
    ]


def _allocate_epics(
    epics_df: pd.DataFrame,
    capacity: CapacityConfig,
    mondays: list[date],
    week_labels: list[str],
    n_base_weeks: int,
) -> list[dict]:
    """
    Distribute each Epic's Estimation across weeks, sorted by Priority.

    Allocation mode is read from the optional ``Allocation Mode`` column:

    * **Sprint** (default): claim up to ``MAX_WEEKLY_ALLOC_PW`` per week, sequential.
    * **Uniform**: spread ``Estimation / n_base_weeks`` evenly, sequential.
    * **Gaps**: Sprint rate but without the sequential minimum — a week
      may receive 0 even when capacity > 0.

    Sequential means: once an epic starts, every subsequent week with available
    capacity must receive ≥ 0.1 PW.

    After the mode-specific first pass, each epic gets a top-up pass to close any
    remaining estimate gap above ``_ESTIMATE_TOLERANCE_PW``.

    Priority guard (quarter scope): if any higher-priority epic is unfinished in
    the primary quarter, lower priorities may start but cannot finish in that
    same quarter.
    """
    n_weeks = len(mondays)
    rows: list[dict] = []

    sorted_epics = epics_df.sort_values(COL_PRIORITY, kind="stable")
    remaining: list[float] = [capacity.eng_net_for(m) for m in mondays]
    has_mode_col = COL_ALLOC_MODE in epics_df.columns
    has_dep_col = COL_DEPENDS_ON in epics_df.columns
    unfinished_priorities_in_quarter: set[float] = set()

    # Track first and last allocated week index per epic name (for dependency resolution).
    epic_first_week: dict[str, int] = {}
    epic_last_week: dict[str, int] = {}

    for _, epic in sorted_epics.iterrows():
        estimation = float(epic[COL_ESTIMATION])
        priority = float(epic[COL_PRIORITY])
        block_quarter_completion = any(p < priority for p in unfinished_priorities_in_quarter)

        # --- resolve allocation mode ---
        if has_mode_col:
            raw = epic[COL_ALLOC_MODE]
            mode = str(raw).strip() if pd.notna(raw) else ""
        else:
            mode = ""
        if mode not in VALID_ALLOC_MODES:
            mode = ALLOC_MODE_DEFAULT

        # --- resolve dependency start constraint ---
        earliest_start_idx = 0
        if has_dep_col:
            raw_dep = epic.get(COL_DEPENDS_ON, None)
            dep_name = str(raw_dep).strip() if pd.notna(raw_dep) and str(raw_dep).strip() else ""
            if dep_name:
                last_idx = epic_last_week.get(dep_name, -1)
                earliest_start_idx = last_idx + 1 if last_idx >= 0 else 0

        # --- per-mode settings ---
        if mode == ALLOC_MODE_UNIFORM:
            weekly_ideal = (
                max(round(estimation / n_base_weeks, 1), 0.1) if estimation > 0 else 0.0
            )
            enforce_sequential = True
        else:
            # Sprint and Gaps both target MAX_WEEKLY_ALLOC_PW
            weekly_ideal = MAX_WEEKLY_ALLOC_PW if estimation > 0 else 0.0
            enforce_sequential = (mode != ALLOC_MODE_GAPS)

        allocations: list[float] = []
        total_allocated = 0.0
        quarter_allocated = 0.0
        weekly_cap = None if mode == ALLOC_MODE_UNIFORM else MAX_WEEKLY_ALLOC_PW

        # ---- Phase 1: Q weeks ----
        for i in range(n_base_weeks):
            if i < earliest_start_idx:
                allocations.append(0.0)
                continue
            budget_left = round(estimation - total_allocated, 1)
            if block_quarter_completion:
                # Keep this epic unfinished in Q by at least 0.1 PW.
                quarter_cap = max(round(estimation - 0.1, 1), 0.0)
                budget_left = min(budget_left, round(quarter_cap - quarter_allocated, 1))
            if budget_left <= 1e-9 or remaining[i] <= 1e-9:
                alloc = 0.0
            else:
                alloc = round(min(weekly_ideal, remaining[i], budget_left), 1)
                if enforce_sequential and alloc < 0.1:
                    alloc = round(min(0.1, remaining[i], budget_left), 1)
            allocations.append(alloc)
            remaining[i] = round(remaining[i] - alloc, 1)
            total_allocated = round(total_allocated + alloc, 1)
            quarter_allocated = round(quarter_allocated + alloc, 1)

        # ---- Top-up Q weeks before touching overflow ----
        if not block_quarter_completion:
            total_allocated = _top_up_epic_allocations_in_window(
                estimation=estimation,
                allocations=allocations,
                remaining=remaining,
                total_allocated=total_allocated,
                start_idx=max(0, earliest_start_idx),
                end_idx=n_base_weeks,
                weekly_cap=weekly_cap,
            )
        quarter_allocated = round(sum(allocations), 1)  # all slots are Q at this point

        # ---- Phase 2: overflow weeks (if budget remains) ----
        for i in range(n_base_weeks, n_weeks):
            if i < earliest_start_idx:
                allocations.append(0.0)
                continue
            budget_left = round(estimation - total_allocated, 1)
            if budget_left <= 1e-9 or remaining[i] <= 1e-9:
                alloc = 0.0
            else:
                alloc = round(min(weekly_ideal, remaining[i], budget_left), 1)
                if enforce_sequential and alloc < 0.1:
                    alloc = round(min(0.1, remaining[i], budget_left), 1)
            allocations.append(alloc)
            remaining[i] = round(remaining[i] - alloc, 1)
            total_allocated = round(total_allocated + alloc, 1)

        # ---- Top-up overflow weeks if still needed ----
        if estimation - total_allocated > _ESTIMATE_TOLERANCE_PW and n_base_weeks < n_weeks:
            total_allocated = _top_up_epic_allocations_in_window(
                estimation=estimation,
                allocations=allocations,
                remaining=remaining,
                total_allocated=total_allocated,
                start_idx=max(n_base_weeks, earliest_start_idx),
                end_idx=n_weeks,
                weekly_cap=weekly_cap,
            )

        # ---- Record first/last allocated week for dependency resolution ----
        epic_name = str(epic[COL_EPIC])
        first_idx = next((i for i, a in enumerate(allocations) if a > 0), None)
        last_idx = max((i for i, a in enumerate(allocations) if a > 0), default=None)
        if first_idx is not None:
            epic_first_week[epic_name] = first_idx
        if last_idx is not None:
            epic_last_week[epic_name] = last_idx

        quarter_allocated = round(sum(allocations[:n_base_weeks]), 1)
        if estimation - quarter_allocated > _ESTIMATE_TOLERANCE_PW:
            unfinished_priorities_in_quarter.add(priority)

        total_weeks = round(sum(allocations[:n_base_weeks]), 1)
        off_estimate = abs(round(total_weeks - estimation, 10)) > _ESTIMATE_TOLERANCE_PW
        row: dict = {
            OUT_COL_BUDGET_BUCKET: epic[COL_BUDGET_BUCKET],
            OUT_COL_EPIC: epic[COL_EPIC],
            OUT_COL_PRIORITY: epic.get(COL_PRIORITY, ""),
            OUT_COL_ESTIMATION: estimation,
            OUT_COL_TOTAL_WEEKS: total_weeks,
            OUT_COL_OFF_ESTIMATE: off_estimate,
        }
        row.update(dict(zip(week_labels, allocations)))
        rows.append(row)

    return rows


def _top_up_epic_allocations_in_window(
    estimation: float,
    allocations: list[float],
    remaining: list[float],
    total_allocated: float,
    start_idx: int,
    end_idx: int,
    weekly_cap: float | None,
) -> float:
    """Consume available weekly capacity to reduce an epic's estimate deficit."""
    for i in range(start_idx, end_idx):
        deficit = round(estimation - total_allocated, 10)
        if deficit <= _ESTIMATE_TOLERANCE_PW:
            break
        if remaining[i] <= 1e-9:
            continue

        week_room = remaining[i]
        if weekly_cap is not None:
            week_room = min(week_room, round(weekly_cap - allocations[i], 10))
        if week_room <= 1e-9:
            continue

        # Preserve 0.1 PW granularity while never exceeding the epic estimate.
        add = math.floor(min(week_room, deficit) * 10 + 1e-9) / 10
        if add <= 1e-9:
            continue

        allocations[i] = round(allocations[i] + add, 1)
        remaining[i] = round(remaining[i] - add, 1)
        total_allocated = round(total_allocated + add, 1)

    return total_allocated


def _build_total_row(epic_rows: list[dict], week_labels: list[str]) -> dict:
    row: dict = {
        OUT_COL_BUDGET_BUCKET: LABEL_TOTAL_BUCKET,
        OUT_COL_EPIC: LABEL_TOTAL_ROW,
        OUT_COL_PRIORITY: "",
        OUT_COL_ESTIMATION: round(sum(r[OUT_COL_ESTIMATION] for r in epic_rows), 1),
        OUT_COL_TOTAL_WEEKS: round(sum(r[OUT_COL_TOTAL_WEEKS] for r in epic_rows), 1),
        OUT_COL_OFF_ESTIMATE: "",
    }
    for w in week_labels:
        row[w] = round(sum(r[w] for r in epic_rows), 1)
    return row


def _build_capacity_alert_row(
    total_row: dict, capacity: CapacityConfig, mondays: list[date], week_labels: list[str]
) -> dict:
    row: dict = {
        OUT_COL_BUDGET_BUCKET: "",
        OUT_COL_EPIC: LABEL_CAPACITY_ALERT_ROW,
        OUT_COL_PRIORITY: "",
        OUT_COL_ESTIMATION: "",
        OUT_COL_TOTAL_WEEKS: "",
        OUT_COL_OFF_ESTIMATE: "",
    }
    for w, monday in zip(week_labels, mondays):
        weekly_total = float(total_row[w])
        row[w] = abs(round(weekly_total - capacity.eng_net_for(monday), 10)) > 0.1
    return row
