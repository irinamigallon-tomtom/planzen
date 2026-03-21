"""
Tests for core_logic.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from planzen.config import (
    LABEL_ENG_NET,
    LABEL_TOTAL_ROW,
    OUT_COL_EPIC,
    OUT_COL_TOTAL_WEEKS,
)
from planzen.core_logic import CapacityConfig, build_output_table

CAPACITY = CapacityConfig(
    num_engineers=5,
    num_managers=2,
)

EPICS_DF = pd.DataFrame(
    [
        {
            "Epics": "Auth & Identity Management",
            "Estimation": 80.0,
            "Budget Bucket": "Platform",
            "Priority": 0,
            "Milestone": "Q1",
        },
        {
            "Epics": "Real-time Analytics",
            "Estimation": 40.0,
            "Budget Bucket": "Analytics",
            "Priority": 1,
            "Milestone": "Q2",
        },
    ]
)

START = date(2026, 1, 5)  # First Monday of 2026
END = date(2026, 1, 26)   # 4 Mondays total


def _build() -> pd.DataFrame:
    return build_output_table(EPICS_DF, CAPACITY, START, END)


def test_output_has_correct_number_of_rows() -> None:
    df = _build()
    # 6 capacity header rows + 2 epic rows + 1 total row
    assert len(df) == 9


def test_week_columns_are_present() -> None:
    df = _build()
    # 4 Mondays: Jan 5, 12, 19, 26
    for label in ["1.05", "1.12", "1.19", "1.26"]:
        assert label in df.columns, f"Missing week column: {label}"


def test_epic_total_does_not_exceed_estimation() -> None:
    df = _build()
    header_labels = {
        "Engineering Capacity (Bruto)", "Engineering Absence",
        "Engineering Net Capacity", "Management Capacity",
        "Management Absence", "Management Net Capacity", "Weekly Allocation",
    }
    epic_rows = df[~df[OUT_COL_EPIC].isin(header_labels)]
    for _, row in epic_rows.iterrows():
        assert row[OUT_COL_TOTAL_WEEKS] <= row["Estimation"] + 1e-9


def test_weekly_total_does_not_exceed_net_capacity() -> None:
    df = _build()
    net_capacity_row = df[df[OUT_COL_EPIC] == LABEL_ENG_NET].iloc[0]
    total_row = df[df[OUT_COL_EPIC] == LABEL_TOTAL_ROW].iloc[0]

    week_cols = [c for c in df.columns if c not in
                 ["Budget Bucket", "Epic / Capacity Metric", "Priority",
                  "Estimation", "Total Weeks"]]
    for w in week_cols:
        assert total_row[w] <= net_capacity_row[w] + 1e-9


def test_eng_net_capacity_is_bruto_minus_absence() -> None:
    assert CAPACITY.eng_net == round(CAPACITY.eng_bruto - CAPACITY.eng_absence, 1)


def test_absence_is_one_twelfth_of_headcount() -> None:
    # 37 absence days/year ÷ 52 weeks ÷ 5 days/week = 0.142 PW/person/week
    from planzen.config import ABSENCE_PW_PER_PERSON
    assert CAPACITY.eng_bruto == 5.0
    assert CAPACITY.eng_absence == round(5 * ABSENCE_PW_PER_PERSON, 1)
    assert CAPACITY.mgmt_capacity == 2.0
    assert CAPACITY.mgmt_absence == round(2 * ABSENCE_PW_PER_PERSON, 1)


def test_mgmt_net_capacity_row_present() -> None:
    df = _build()
    assert "Management Net Capacity" in df[OUT_COL_EPIC].values


def test_mgmt_net_is_capacity_minus_absence() -> None:
    assert CAPACITY.mgmt_net == round(CAPACITY.mgmt_capacity - CAPACITY.mgmt_absence, 1)
