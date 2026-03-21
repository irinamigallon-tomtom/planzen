"""
Tests for core_logic.py
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import pandas as pd

from planzen.config import FISCAL_QUARTERS
from planzen.core_logic import (
    CapacityConfig,
    build_output_table,
    get_quarter_dates,
    validate_allocation,
    _mondays_in_range,
)
from planzen.config import (
    ABSENCE_PW_PER_PERSON,
    ALLOC_MODE_GAPS,
    ALLOC_MODE_SPRINT,
    ALLOC_MODE_UNIFORM,
    LABEL_CAPACITY_ALERT_ROW,
    LABEL_ENG_NET,
    LABEL_TOTAL_ROW,
    MAX_WEEKLY_ALLOC_PW,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_OFF_ESTIMATE,
    OUT_COL_TOTAL_WEEKS,
)

CAPACITY = CapacityConfig(num_engineers=5, num_managers=2)

_WEEK_COLS_SET = {
    "Budget Bucket", "Epic Description", "Priority", "Estimation",
    "Total Weeks", "Off Estimate",
}

_NON_EPIC_LABELS = {
    "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
    "Management Capacity (Bruto)", "Management Absence", "Management Net Capacity",
    "Weekly Allocation", "Off Capacity",
}

EPICS_DF = pd.DataFrame([
    {
        "Epic Description": "Auth & Identity Management",
        "Estimation": 80.0,
        "Budget Bucket": "Platform",
        "Type": "Feature",
        "Link": "https://jira.example.com/AUTH-1",
        "Priority": 0,
        "Milestone": "Q1",
    },
    {
        "Epic Description": "Real-time Analytics",
        "Estimation": 40.0,
        "Budget Bucket": "Analytics",
        "Type": "Feature",
        "Link": "https://jira.example.com/ANA-1",
        "Priority": 1,
        "Milestone": "Q2",
    },
])

# Use Q1 start; narrow to 4 Mondays for fast tests
_Q1_START = FISCAL_QUARTERS[1][0]
START = _Q1_START
END = _Q1_START + timedelta(weeks=3)  # 4 Mondays: Dec 29, Jan 5, Jan 12, Jan 19


def _build(epics=EPICS_DF, capacity=CAPACITY) -> pd.DataFrame:
    return build_output_table(epics, capacity, START, END)


@pytest.fixture
def output_df() -> pd.DataFrame:
    return _build()


def _week_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in _WEEK_COLS_SET]


def _epic_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df[OUT_COL_EPIC].isin(_NON_EPIC_LABELS)]


# ---------------------------------------------------------------------------
# Quarter date tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "quarter, expected_start, expected_end",
    [
        (1, date(2025, 12, 29), date(2026, 3, 23)),
        (2, date(2026, 3, 30), date(2026, 6, 22)),
        (3, date(2026, 6, 29), date(2026, 9, 21)),
        (4, date(2026, 9, 28), date(2026, 12, 21)),
    ],
)
def test_get_quarter_dates(quarter: int, expected_start: date, expected_end: date) -> None:
    start, end = get_quarter_dates(quarter)
    assert start == expected_start
    assert end == expected_end


def test_get_quarter_dates_invalid() -> None:
    with pytest.raises(ValueError, match="Quarter must be 1"):
        get_quarter_dates(5)


def test_each_quarter_has_13_mondays() -> None:
    from planzen.core_logic import _mondays_in_range
    for q, (start, end) in FISCAL_QUARTERS.items():
        mondays = _mondays_in_range(start, end)
        assert len(mondays) == 13, f"Q{q} has {len(mondays)} Mondays, expected 13"


# ---------------------------------------------------------------------------
# Output structure tests
# ---------------------------------------------------------------------------

def test_output_has_correct_number_of_rows(output_df: pd.DataFrame) -> None:
    # 6 capacity header rows + 2 epic rows + 1 total row + 1 off-capacity row
    assert len(output_df) == 10


def test_week_columns_are_present(output_df: pd.DataFrame) -> None:
    # Q1 starts 2025-12-29; 4 Mondays: Dec 29, Jan 5, Jan 12, Jan 19
    for label in ["Dec.29", "Jan.05", "Jan.12", "Jan.19"]:
        assert label in output_df.columns, f"Missing week column: {label}"


def test_epic_total_does_not_exceed_estimation(output_df: pd.DataFrame) -> None:
    epic_rows = _epic_rows(output_df)
    for _, row in epic_rows.iterrows():
        assert row[OUT_COL_TOTAL_WEEKS] <= row[OUT_COL_ESTIMATION] + 1e-9


def test_weekly_total_does_not_exceed_net_capacity(output_df: pd.DataFrame) -> None:
    net_capacity_row = output_df[output_df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]
    total_row = output_df[output_df[OUT_COL_EPIC] == LABEL_TOTAL_ROW].iloc[0]
    week_cols = _week_cols(output_df)
    for w in week_cols:
        assert total_row[w] <= net_capacity_row[w] + 1e-9


@pytest.mark.parametrize("sum_col", [OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS])
def test_total_row_is_sum_of_epics(output_df: pd.DataFrame, sum_col: str) -> None:
    total_row = output_df[output_df[OUT_COL_EPIC] == LABEL_TOTAL_ROW].iloc[0]
    expected = round(_epic_rows(output_df)[sum_col].sum(), 1)
    assert total_row[sum_col] == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("num_engineers, num_managers", [(5.0, 2.0), (2.5, 0.5)])
def test_capacity_config_derived_values(num_engineers: float, num_managers: float) -> None:
    cap = CapacityConfig(num_engineers=num_engineers, num_managers=num_managers)
    expected_eng_absence = round(num_engineers * ABSENCE_PW_PER_PERSON, 1)
    expected_mgmt_absence = round(num_managers * ABSENCE_PW_PER_PERSON, 1)

    assert cap.eng_bruto == num_engineers
    assert cap.eng_absence == expected_eng_absence
    assert cap.eng_net == round(num_engineers - expected_eng_absence, 1)
    assert cap.mgmt_capacity == num_managers
    assert cap.mgmt_absence == expected_mgmt_absence
    assert cap.mgmt_net == round(num_managers - expected_mgmt_absence, 1)


# ---------------------------------------------------------------------------
# Sequential allocation tests
# ---------------------------------------------------------------------------

def test_epics_sorted_by_priority_in_output() -> None:
    """Epics must appear sorted by Priority ascending in the output."""
    # Supply epics in reverse priority order to confirm sorting.
    reversed_epics = EPICS_DF.iloc[::-1].reset_index(drop=True)
    df = _build(epics=reversed_epics)
    epic_rows = _epic_rows(df)
    priorities = list(epic_rows["Priority"])
    assert priorities == sorted(priorities), f"Epics not sorted by priority: {priorities}"


def test_no_gap_when_capacity_available() -> None:
    """Once an epic starts, every week with available capacity must get ≥ 0.1 PW."""
    single_epic = pd.DataFrame([{
        "Epic Description": "Solo Epic", "Estimation": 50.0,
        "Budget Bucket": "Core", "Type": "Feature", "Link": "link", "Priority": 0, "Milestone": "Q1",
    }])
    df = build_output_table(single_epic, CAPACITY, START, END)
    week_cols = _week_cols(df)
    epic_row = df[df[OUT_COL_EPIC] == "Solo Epic"].iloc[0]
    net_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]

    for w in week_cols:
        if net_row[w] > 0:
            assert epic_row[w] >= 0.1, f"Gap in week {w} despite available capacity"


def test_gap_admissible_when_capacity_exhausted() -> None:
    """Lower-priority epic gets 0 when a Uniform high-priority epic fills all capacity."""
    greedy_epics = pd.DataFrame([
        {"Epic Description": "Greedy", "Estimation": 999.0, "Budget Bucket": "A",
         "Type": "Feature", "Link": "link-g", "Priority": 0, "Milestone": "Q1",
         "Allocation Mode": ALLOC_MODE_UNIFORM},   # Uniform → fills all capacity
        {"Epic Description": "Starved", "Estimation": 10.0,  "Budget Bucket": "B",
         "Type": "Feature", "Link": "link-s", "Priority": 1, "Milestone": "Q1",
         "Allocation Mode": ALLOC_MODE_UNIFORM},
    ])
    df = build_output_table(greedy_epics, CAPACITY, START, END)
    week_cols = _week_cols(df)
    greedy_row = df[df[OUT_COL_EPIC] == "Greedy"].iloc[0]
    starved_row = df[df[OUT_COL_EPIC] == "Starved"].iloc[0]
    net_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]

    for w in week_cols:
        if greedy_row[w] >= net_row[w]:
            assert starved_row[w] == 0.0, (
                f"Starved should be 0 in {w} (capacity exhausted by Greedy), got {starved_row[w]}"
            )


# ---------------------------------------------------------------------------
# validate_allocation tests
# ---------------------------------------------------------------------------

def _week_mondays(df: pd.DataFrame) -> list:
    """Return a list of N sequential Mondays matching the week columns count.

    The exact dates don't matter for tests using constant-capacity CapacityConfig
    (no per-week dicts), but validate_allocation requires the same length as
    the week columns.
    """
    n = len(_week_cols(df))
    base = date(2026, 3, 30)
    return [base + timedelta(weeks=i) for i in range(n)]


def test_validate_allocation_passes_for_valid_output(output_df: pd.DataFrame) -> None:
    violations = validate_allocation(output_df, CAPACITY, _week_mondays(output_df))
    assert violations == [], f"Unexpected violations: {violations}"


def test_validate_allocation_detects_epic_overallocation() -> None:
    df = _build()
    week_cols = _week_cols(df)
    epic_mask = df[OUT_COL_EPIC] == "Auth & Identity Management"
    df.loc[epic_mask, week_cols[0]] = 9999.0
    df.loc[epic_mask, OUT_COL_TOTAL_WEEKS] = 9999.0
    violations = validate_allocation(df, CAPACITY, _week_mondays(df))
    assert any("Auth & Identity Management" in v for v in violations)


def test_validate_allocation_detects_weekly_overallocation() -> None:
    df = _build()
    week_cols = _week_cols(df)
    epic_mask = ~df[OUT_COL_EPIC].isin(_NON_EPIC_LABELS)
    df.loc[epic_mask, week_cols[0]] = 9999.0
    violations = validate_allocation(df, CAPACITY, _week_mondays(df))
    assert any(week_cols[0] in v for v in violations)


def test_overflow_scenario_is_valid() -> None:
    """Epic with huge estimation partially fills the quarter — not a violation."""
    overflow_epics = pd.DataFrame([{
        "Epic Description": "Huge Epic", "Estimation": 999.0,
        "Budget Bucket": "All", "Type": "Feature", "Link": "link", "Priority": 0, "Milestone": "Q4",
    }])
    capacity = CapacityConfig(num_engineers=1, num_managers=0)
    df = build_output_table(overflow_epics, capacity, START, END)
    violations = validate_allocation(df, capacity, _week_mondays(df))
    assert violations == [], f"Unexpected violations: {violations}"

    week_cols = _week_cols(df)
    epic_row = df[df[OUT_COL_EPIC] == "Huge Epic"].iloc[0]
    assert epic_row[OUT_COL_TOTAL_WEEKS] <= 999.0
    assert epic_row[OUT_COL_TOTAL_WEEKS] <= capacity.eng_net * len(week_cols) + 1e-9


# ---------------------------------------------------------------------------
# Off Estimate and Off Capacity tests
# ---------------------------------------------------------------------------

def test_off_estimate_true_when_partially_allocated(output_df: pd.DataFrame) -> None:
    """Epic that can't be fully allocated (estimation >> capacity) has Off Estimate = True."""
    # EPICS_DF has 80 PW and 40 PW epics; with 4 weeks they are never fully allocated
    epic_rows = _epic_rows(output_df)
    for _, row in epic_rows.iterrows():
        assert row[OUT_COL_OFF_ESTIMATE] is True


def test_off_estimate_false_when_exactly_allocated() -> None:
    """Epic whose total weeks equals estimation has Off Estimate = False."""
    # estimation=0.2 PW, 4 weeks, capacity=4.3/week -> fully allocated in ~1 week
    tiny_epic = pd.DataFrame([{
        "Epic Description": "Tiny",
        "Estimation": 0.2,
        "Budget Bucket": "Core",
        "Type": "Feature",
        "Link": "link",
        "Priority": 0,
        "Milestone": "Q1",
    }])
    df = build_output_table(tiny_epic, CAPACITY, START, END)
    epic_row = df[df[OUT_COL_EPIC] == "Tiny"].iloc[0]
    assert epic_row[OUT_COL_OFF_ESTIMATE] is False


def test_off_capacity_true_when_weekly_total_differs() -> None:
    """Off Capacity = True when weekly total deviates from eng_net by > 0.1."""
    # Single small epic (estimation=0.2) fills only 0.1/week for 2 weeks → total << eng_net=4.3
    tiny_epic = pd.DataFrame([{
        "Epic Description": "Tiny",
        "Estimation": 0.2,
        "Budget Bucket": "Core",
        "Type": "Feature",
        "Link": "link",
        "Priority": 0,
        "Milestone": "Q1",
    }])
    df = build_output_table(tiny_epic, CAPACITY, START, END)
    alert_row = df[df[OUT_COL_EPIC] == LABEL_CAPACITY_ALERT_ROW].iloc[0]
    week_cols = _week_cols(df)
    # Weekly total (max 0.1) is far below eng_net=4.3 → all weeks are off
    for w in week_cols:
        assert alert_row[w] is True


def test_off_capacity_false_when_weekly_total_at_capacity() -> None:
    """Off Capacity = False when weekly total is within 0.1 of eng_net."""
    # eng_net for 1 engineer = 1.0 - round(1 * 0.1423, 1) = 1.0 - 0.1 = 0.9 PW/week
    # estimation = 0.9 * 4 = 3.6 PW, weekly_ideal = round(3.6/4, 1) = 0.9 → 4×0.9=3.6 = est
    cap = CapacityConfig(num_engineers=1, num_managers=0)
    exact_epic = pd.DataFrame([{
        "Epic Description": "Exact",
        "Estimation": 3.6,
        "Budget Bucket": "Core",
        "Type": "Feature",
        "Link": "link",
        "Priority": 0,
        "Milestone": "Q1",
    }])
    df = build_output_table(exact_epic, cap, START, END)
    alert_row = df[df[OUT_COL_EPIC] == LABEL_CAPACITY_ALERT_ROW].iloc[0]
    week_cols = _week_cols(df)
    for w in week_cols:
        assert alert_row[w] is False


# ---------------------------------------------------------------------------
# Allocation mode tests
# ---------------------------------------------------------------------------

def _make_single_epic(estimation: float, mode: str, priority: int = 0) -> pd.DataFrame:
    return pd.DataFrame([{
        "Epic Description": "E",
        "Estimation": estimation,
        "Budget Bucket": "Core",
        "Type": "Feature",
        "Link": "link",
        "Priority": priority,
        "Milestone": "Q1",
        "Allocation Mode": mode,
    }])


def test_sprint_caps_at_max_weekly_alloc() -> None:
    """Sprint: no week may exceed MAX_WEEKLY_ALLOC_PW for a single epic."""
    df = build_output_table(_make_single_epic(50.0, ALLOC_MODE_SPRINT), CAPACITY, START, END)
    week_cols = _week_cols(df)
    row = df[df[OUT_COL_EPIC] == "E"].iloc[0]
    for w in week_cols:
        assert row[w] <= MAX_WEEKLY_ALLOC_PW + 1e-9, (
            f"Sprint exceeded cap in {w}: {row[w]}"
        )


def test_sprint_is_sequential() -> None:
    """Sprint: once started, every week with available capacity gets ≥ 0.1 PW."""
    df = build_output_table(_make_single_epic(50.0, ALLOC_MODE_SPRINT), CAPACITY, START, END)
    week_cols = _week_cols(df)
    row = df[df[OUT_COL_EPIC] == "E"].iloc[0]
    net_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]
    for w in week_cols:
        if net_row[w] > 0:
            assert row[w] >= 0.1, f"Sprint gap in {w} despite available capacity"


def test_uniform_distributes_evenly() -> None:
    """Uniform: allocation per week equals round(estimation / n_weeks, 1)."""
    cap = CapacityConfig(num_engineers=5, num_managers=0)
    # 4 weeks, estimation=2.0 → weekly_ideal = round(2.0/4, 1) = 0.5
    df = build_output_table(_make_single_epic(2.0, ALLOC_MODE_UNIFORM), cap, START, END)
    week_cols = _week_cols(df)
    row = df[df[OUT_COL_EPIC] == "E"].iloc[0]
    expected = round(2.0 / len(week_cols), 1)
    for w in week_cols:
        assert row[w] == pytest.approx(expected, abs=1e-6), (
            f"Uniform week {w}: expected {expected}, got {row[w]}"
        )


def test_uniform_is_sequential() -> None:
    """Uniform: once started, every week with capacity gets ≥ 0.1 PW (while budget remains)."""
    # Use 999 PW so budget is never exhausted — all weeks must be non-zero
    df = build_output_table(_make_single_epic(999.0, ALLOC_MODE_UNIFORM), CAPACITY, START, END)
    week_cols = _week_cols(df)
    row = df[df[OUT_COL_EPIC] == "E"].iloc[0]
    net_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]
    for w in week_cols:
        if net_row[w] > 0:
            assert row[w] >= 0.1, f"Uniform gap in {w} despite available capacity"


def test_uniform_rounding_top_up_happens_before_lower_priority_starts() -> None:
    """A higher-priority Uniform epic must be topped up to estimate before lower priorities consume capacity."""
    q1_start, q1_end = FISCAL_QUARTERS[1]
    epics = pd.DataFrame([
        {
            "Epic Description": "Top",
            "Estimation": 4.0,
            "Budget Bucket": "Core",
            "Type": "Feature",
            "Link": "link-top",
            "Priority": 0,
            "Milestone": "Q1",
            "Allocation Mode": ALLOC_MODE_UNIFORM,
        },
        {
            "Epic Description": "Lower",
            "Estimation": 10.0,
            "Budget Bucket": "Core",
            "Type": "Feature",
            "Link": "link-low",
            "Priority": 1,
            "Milestone": "Q1",
            "Allocation Mode": ALLOC_MODE_SPRINT,
        },
    ])
    df = build_output_table(epics, CAPACITY, q1_start, q1_end)
    top_row = df[df[OUT_COL_EPIC] == "Top"].iloc[0]
    lower_row = df[df[OUT_COL_EPIC] == "Lower"].iloc[0]

    # 4.0 / 13 rounds to 0.3, so a naive Uniform pass would produce 3.9.
    # The allocator must top up the higher-priority epic before lower priorities.
    assert top_row[OUT_COL_TOTAL_WEEKS] == pytest.approx(4.0, abs=1e-6)
    assert top_row[OUT_COL_OFF_ESTIMATE] is False
    assert lower_row[OUT_COL_TOTAL_WEEKS] <= 10.0 + 1e-9


def test_lower_priority_may_start_but_not_finish_if_higher_priority_unfinished_in_quarter() -> None:
    """If priority N is unfinished in quarter, priority N+1 cannot finish in that quarter."""
    epics = pd.DataFrame([
        {
            "Epic Description": "Higher",
            "Estimation": 10.0,
            "Budget Bucket": "Core",
            "Type": "Feature",
            "Link": "link-high",
            "Priority": 0,
            "Milestone": "Q1",
            "Allocation Mode": ALLOC_MODE_SPRINT,
        },
        {
            "Epic Description": "Lower",
            "Estimation": 2.0,
            "Budget Bucket": "Core",
            "Type": "Feature",
            "Link": "link-low",
            "Priority": 1,
            "Milestone": "Q1",
            "Allocation Mode": ALLOC_MODE_SPRINT,
        },
    ])
    df = build_output_table(epics, CAPACITY, START, END)
    higher_row = df[df[OUT_COL_EPIC] == "Higher"].iloc[0]
    lower_row = df[df[OUT_COL_EPIC] == "Lower"].iloc[0]

    week_cols = _week_cols(df)
    quarter_weeks = week_cols[:4]
    higher_q = round(sum(float(higher_row[w]) for w in quarter_weeks), 1)
    lower_q = round(sum(float(lower_row[w]) for w in quarter_weeks), 1)

    # Priority 0 cannot finish in 4 weeks with Sprint cap (2.0/week -> 8.0 max).
    assert higher_q < higher_row[OUT_COL_ESTIMATION] - 0.05
    # Priority 1 may start in the quarter, but must remain unfinished there.
    assert lower_q > 0.0
    assert lower_q < lower_row[OUT_COL_ESTIMATION] - 0.05


def test_gaps_allowed_skips_weeks_below_minimum() -> None:
    """Gaps: if remaining capacity rounds below 0.1, week gets 0 (no forcing)."""
    # Use 2 epics: Sprint eats 2.0/week, leaving 2.3 for gaps epic.
    # Then add a third tiny epic: if capacity remaining rounds to < 0.1, gaps gets 0.
    # Easiest: 1 engineer (eng_net ≈ 0.9/week). Sprint epic: 0.9/week (capped by capacity).
    # Then gaps epic: remaining = 0. Gets 0 every week. That's fine — tests 0 when capacity=0.
    # Better test: force remaining < 0.1 by saturating with multiple Sprint epics.
    cap = CapacityConfig(num_engineers=1, num_managers=0)  # eng_net ≈ 0.9
    epics = pd.DataFrame([
        {"Epic Description": "Filler", "Estimation": 999.0, "Budget Bucket": "C",
         "Type": "F", "Link": "l1", "Priority": 0, "Milestone": "Q1",
         "Allocation Mode": ALLOC_MODE_SPRINT},   # claims min(2.0, 0.9) = 0.9 each week
        {"Epic Description": "Gaps", "Estimation": 10.0, "Budget Bucket": "C",
         "Type": "F", "Link": "l2", "Priority": 1, "Milestone": "Q1",
         "Allocation Mode": ALLOC_MODE_GAPS},     # nothing left → 0 each week
    ])
    df = build_output_table(epics, cap, START, END)
    week_cols = _week_cols(df)
    gaps_row = df[df[OUT_COL_EPIC] == "Gaps"].iloc[0]
    # All capacity consumed by Filler → Gaps gets 0 without sequential forcing
    for w in week_cols:
        assert gaps_row[w] == 0.0, f"Gaps got non-zero in {w}: {gaps_row[w]}"


@pytest.mark.parametrize("mode", ["", "Turbo"])
def test_invalid_or_blank_alloc_mode_falls_back_to_sprint(mode: str) -> None:
    """Blank or unrecognised Allocation Mode is treated as Sprint."""
    if mode:
        candidate = _make_single_epic(50.0, mode)
    else:
        candidate = pd.DataFrame([{
            "Epic Description": "E", "Estimation": 50.0, "Budget Bucket": "Core",
            "Type": "F", "Link": "l", "Priority": 0, "Milestone": "Q1",
        }])

    sprint = _make_single_epic(50.0, ALLOC_MODE_SPRINT)
    df_candidate = build_output_table(candidate, CAPACITY, START, END)
    df_sprint = build_output_table(sprint, CAPACITY, START, END)
    week_cols = _week_cols(df_candidate)
    row_candidate = df_candidate[df_candidate[OUT_COL_EPIC] == "E"].iloc[0]
    row_sprint = df_sprint[df_sprint[OUT_COL_EPIC] == "E"].iloc[0]
    for w in week_cols:
        assert row_candidate[w] == row_sprint[w]

# ---------------------------------------------------------------------------
# Overflow tests  (automatic: triggers when Σ(Estimation) > eng_net × n_weeks)
# ---------------------------------------------------------------------------

def test_overflow_extends_week_columns() -> None:
    """When total estimation exceeds quarter capacity, output has 26 week columns."""
    # EPICS_DF total = 120+80 = 200 PW >> Q1 capacity (~55 PW) → overflow
    q1_start, q1_end = FISCAL_QUARTERS[1]
    df = build_output_table(EPICS_DF, CAPACITY, q1_start, q1_end)
    week_cols = _week_cols(df)
    assert len(week_cols) == 26, f"Expected 26 week columns, got {len(week_cols)}"


def test_overflow_week_labels_span_both_quarters() -> None:
    """Week column headers should include Mondays from Q1 and Q2."""
    q1_start, q1_end = FISCAL_QUARTERS[1]
    df = build_output_table(EPICS_DF, CAPACITY, q1_start, q1_end)
    cols = list(df.columns)
    assert "Dec.29" in cols   # first Q1 Monday
    assert "Jun.22" in cols   # last Q2 Monday


def test_overflow_respects_capacity_constraint() -> None:
    """Even with overflow, no week may exceed Engineer Net Capacity."""
    q1_start, q1_end = FISCAL_QUARTERS[1]
    df = build_output_table(EPICS_DF, CAPACITY, q1_start, q1_end)
    violations = validate_allocation(df, CAPACITY, _week_mondays(df))
    assert violations == [], f"Violations with overflow: {violations}"


def test_no_overflow_when_estimation_fits() -> None:
    """When total estimation fits within the quarter, output has exactly 13 week columns."""
    q1_start, q1_end = FISCAL_QUARTERS[1]
    tiny = pd.DataFrame([{
        "Epic Description": "Small", "Estimation": 1.0,
        "Budget Bucket": "Core", "Type": "F", "Link": "l", "Priority": 0, "Milestone": "Q1",
    }])
    df = build_output_table(tiny, CAPACITY, q1_start, q1_end)
    week_cols = _week_cols(df)
    assert len(week_cols) == 13
