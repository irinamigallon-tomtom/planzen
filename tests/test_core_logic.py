"""
Tests for core_logic.py
"""

from __future__ import annotations

import pytest
import pandas as pd

from planzen.config import FISCAL_QUARTERS
from planzen.core_logic import (
    CapacityConfig,
    build_output_table,
    get_quarter_dates,
    validate_allocation,
)
from planzen.config import (
    LABEL_CAPACITY_ALERT_ROW,
    LABEL_ENG_NET,
    LABEL_TOTAL_ROW,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_OFF_ESTIMATE,
    OUT_COL_TOTAL_WEEKS,
)

CAPACITY = CapacityConfig(num_engineers=5, num_managers=2)

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
from datetime import timedelta
_Q1_START = FISCAL_QUARTERS[1][0]
START = _Q1_START
END = _Q1_START + timedelta(weeks=3)  # 4 Mondays: Dec 29, Jan 5, Jan 12, Jan 19


def _build(epics=EPICS_DF, capacity=CAPACITY) -> pd.DataFrame:
    return build_output_table(epics, capacity, START, END)


# ---------------------------------------------------------------------------
# Quarter date tests
# ---------------------------------------------------------------------------

def test_get_quarter_dates_q1() -> None:
    from datetime import date
    start, end = get_quarter_dates(1)
    assert start == date(2025, 12, 29)
    assert end == date(2026, 3, 23)  # start + 12 weeks


def test_get_quarter_dates_q2() -> None:
    from datetime import date
    start, end = get_quarter_dates(2)
    assert start == date(2026, 3, 30)
    assert end == date(2026, 6, 22)


def test_get_quarter_dates_q3() -> None:
    from datetime import date
    start, end = get_quarter_dates(3)
    assert start == date(2026, 6, 29)
    assert end == date(2026, 9, 21)


def test_get_quarter_dates_q4() -> None:
    from datetime import date
    start, end = get_quarter_dates(4)
    assert start == date(2026, 9, 28)
    assert end == date(2026, 12, 21)


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

def test_output_has_correct_number_of_rows() -> None:
    df = _build()
    # 6 capacity header rows + 2 epic rows + 1 total row + 1 off-capacity row
    assert len(df) == 10


def test_week_columns_are_present() -> None:
    df = _build()
    # Q1 starts 2025-12-29; 4 Mondays: Dec 29, Jan 5, Jan 12, Jan 19
    for label in ["Dec.29", "Jan.05", "Jan.12", "Jan.19"]:
        assert label in df.columns, f"Missing week column: {label}"


def test_epic_total_does_not_exceed_estimation() -> None:
    df = _build()
    header_labels = {
        "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
        "Management Capacity", "Management Absence", "Management Net Capacity",
        "Weekly Allocation", "Off Capacity",
    }
    epic_rows = df[~df[OUT_COL_EPIC].isin(header_labels)]
    for _, row in epic_rows.iterrows():
        assert row[OUT_COL_TOTAL_WEEKS] <= row[OUT_COL_ESTIMATION] + 1e-9


def test_weekly_total_does_not_exceed_net_capacity() -> None:
    df = _build()
    net_capacity_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]
    total_row = df[df[OUT_COL_EPIC] == LABEL_TOTAL_ROW].iloc[0]
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks", "Off Estimate"}]
    for w in week_cols:
        assert total_row[w] <= net_capacity_row[w] + 1e-9


def test_total_row_estimation_is_sum_of_epics() -> None:
    df = _build()
    total_row = df[df[OUT_COL_EPIC] == LABEL_TOTAL_ROW].iloc[0]
    epic_rows = df[~df[OUT_COL_EPIC].isin({
        "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
        "Management Capacity", "Management Absence", "Management Net Capacity",
        "Weekly Allocation", "Off Capacity",
    })]
    expected = round(epic_rows[OUT_COL_ESTIMATION].sum(), 1)
    assert total_row[OUT_COL_ESTIMATION] == pytest.approx(expected, abs=1e-6)


def test_total_row_total_weeks_is_sum_of_epics() -> None:
    df = _build()
    total_row = df[df[OUT_COL_EPIC] == LABEL_TOTAL_ROW].iloc[0]
    epic_rows = df[~df[OUT_COL_EPIC].isin({
        "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
        "Management Capacity", "Management Absence", "Management Net Capacity",
        "Weekly Allocation", "Off Capacity",
    })]
    expected = round(epic_rows[OUT_COL_TOTAL_WEEKS].sum(), 1)
    assert total_row[OUT_COL_TOTAL_WEEKS] == pytest.approx(expected, abs=1e-6)


def test_eng_net_capacity_is_bruto_minus_absence() -> None:
    assert CAPACITY.eng_net == round(CAPACITY.eng_bruto - CAPACITY.eng_absence, 1)


def test_absence_formula() -> None:
    from planzen.config import ABSENCE_PW_PER_PERSON
    assert CAPACITY.eng_bruto == 5.0
    assert CAPACITY.eng_absence == round(5 * ABSENCE_PW_PER_PERSON, 1)
    assert CAPACITY.mgmt_capacity == 2.0
    assert CAPACITY.mgmt_absence == round(2 * ABSENCE_PW_PER_PERSON, 1)


def test_fractional_fte_capacity() -> None:
    """Headcounts like 2.5 engineers or 0.5 managers must produce correct capacity values."""
    from planzen.config import ABSENCE_PW_PER_PERSON
    cap = CapacityConfig(num_engineers=2.5, num_managers=0.5)
    assert cap.eng_bruto == 2.5
    assert cap.eng_absence == round(2.5 * ABSENCE_PW_PER_PERSON, 1)
    assert cap.eng_net == round(2.5 - round(2.5 * ABSENCE_PW_PER_PERSON, 1), 1)
    assert cap.mgmt_capacity == 0.5
    assert cap.mgmt_absence == round(0.5 * ABSENCE_PW_PER_PERSON, 1)
    assert cap.mgmt_net == round(0.5 - round(0.5 * ABSENCE_PW_PER_PERSON, 1), 1)


def test_mgmt_net_capacity_row_present() -> None:
    df = _build()
    assert "Management Net Capacity" in df[OUT_COL_EPIC].values


def test_mgmt_net_is_capacity_minus_absence() -> None:
    assert CAPACITY.mgmt_net == round(CAPACITY.mgmt_capacity - CAPACITY.mgmt_absence, 1)


# ---------------------------------------------------------------------------
# Sequential allocation tests
# ---------------------------------------------------------------------------

def test_epics_sorted_by_priority_in_output() -> None:
    """Epics must appear sorted by Priority ascending in the output."""
    # Supply epics in reverse priority order to confirm sorting.
    reversed_epics = EPICS_DF.iloc[::-1].reset_index(drop=True)
    df = _build(epics=reversed_epics)
    header_labels = {
        "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
        "Management Capacity", "Management Absence", "Management Net Capacity",
        "Weekly Allocation", "Off Capacity",
    }
    epic_rows = df[~df[OUT_COL_EPIC].isin(header_labels)]
    priorities = list(epic_rows["Priority"])
    assert priorities == sorted(priorities), f"Epics not sorted by priority: {priorities}"


def test_no_gap_when_capacity_available() -> None:
    """Once an epic starts, every week with available capacity must get ≥ 0.1 PW."""
    single_epic = pd.DataFrame([{
        "Epic Description": "Solo Epic", "Estimation": 50.0,
        "Budget Bucket": "Core", "Type": "Feature", "Link": "link", "Priority": 0, "Milestone": "Q1",
    }])
    df = build_output_table(single_epic, CAPACITY, START, END)
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks", "Off Estimate"}]
    epic_row = df[df[OUT_COL_EPIC] == "Solo Epic"].iloc[0]
    net_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]

    for w in week_cols:
        if net_row[w] > 0:
            assert epic_row[w] >= 0.1, f"Gap in week {w} despite available capacity"


def test_gap_admissible_when_capacity_exhausted() -> None:
    """Lower-priority epic gets 0 only when capacity is fully consumed by higher-priority."""
    greedy_epics = pd.DataFrame([
        {"Epic Description": "Greedy", "Estimation": 999.0, "Budget Bucket": "A",
         "Type": "Feature", "Link": "link-g", "Priority": 0, "Milestone": "Q1"},
        {"Epic Description": "Starved", "Estimation": 10.0,  "Budget Bucket": "B",
         "Type": "Feature", "Link": "link-s", "Priority": 1, "Milestone": "Q1"},
    ])
    df = build_output_table(greedy_epics, CAPACITY, START, END)
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks", "Off Estimate"}]
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

def test_validate_allocation_passes_for_valid_output() -> None:
    df = _build()
    violations = validate_allocation(df, CAPACITY)
    assert violations == [], f"Unexpected violations: {violations}"


def test_validate_allocation_detects_epic_overallocation() -> None:
    df = _build()
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks", "Off Estimate"}]
    epic_mask = df[OUT_COL_EPIC] == "Auth & Identity Management"
    df.loc[epic_mask, week_cols[0]] = 9999.0
    df.loc[epic_mask, OUT_COL_TOTAL_WEEKS] = 9999.0
    violations = validate_allocation(df, CAPACITY)
    assert any("Auth & Identity Management" in v for v in violations)


def test_validate_allocation_detects_weekly_overallocation() -> None:
    df = _build()
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks", "Off Estimate"}]
    epic_mask = ~df[OUT_COL_EPIC].isin({
        "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
        "Management Capacity", "Management Absence", "Management Net Capacity",
        "Weekly Allocation", "Off Capacity",
    })
    df.loc[epic_mask, week_cols[0]] = 9999.0
    violations = validate_allocation(df, CAPACITY)
    assert any(week_cols[0] in v for v in violations)


def test_overflow_scenario_is_valid() -> None:
    """Epic with huge estimation partially fills the quarter — not a violation."""
    overflow_epics = pd.DataFrame([{
        "Epic Description": "Huge Epic", "Estimation": 999.0,
        "Budget Bucket": "All", "Type": "Feature", "Link": "link", "Priority": 0, "Milestone": "Q4",
    }])
    capacity = CapacityConfig(num_engineers=1, num_managers=0)
    df = build_output_table(overflow_epics, capacity, START, END)
    violations = validate_allocation(df, capacity)
    assert violations == [], f"Unexpected violations: {violations}"

    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks", "Off Estimate"}]
    epic_row = df[df[OUT_COL_EPIC] == "Huge Epic"].iloc[0]
    assert epic_row[OUT_COL_TOTAL_WEEKS] <= 999.0
    assert epic_row[OUT_COL_TOTAL_WEEKS] <= capacity.eng_net * len(week_cols) + 1e-9


# ---------------------------------------------------------------------------
# Off Estimate and Off Capacity tests
# ---------------------------------------------------------------------------

def test_off_estimate_true_when_partially_allocated() -> None:
    """Epic that can't be fully allocated (estimation >> capacity) has Off Estimate = True."""
    df = _build()
    # EPICS_DF has 80 PW and 40 PW epics; with 4 weeks they are never fully allocated
    epic_rows = df[~df[OUT_COL_EPIC].isin({
        "Engineer Capacity (Bruto)", "Engineer Absence", "Engineer Net Capacity",
        "Management Capacity", "Management Absence", "Management Net Capacity",
        "Weekly Allocation", "Off Capacity",
    })]
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
    df = _build()
    alert_row = df[df[OUT_COL_EPIC] == LABEL_CAPACITY_ALERT_ROW].iloc[0]
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation",
                  "Total Weeks", "Off Estimate"}]
    # With two sprint epics (2.0/week each = 4.0 total) vs eng_net=4.3, all weeks are off
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
    week_cols = [c for c in df.columns if c not in
                 {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation",
                  "Total Weeks", "Off Estimate"}]
    for w in week_cols:
        assert alert_row[w] is False
