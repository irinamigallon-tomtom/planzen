"""
Compute route: runs the allocation algorithm and returns serialised rows.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter

from planzen.core_logic import build_output_table, get_quarter_dates, validate_allocation
from planzen.config import FISCAL_QUARTERS

from bridge import (
    allocation_df_to_rows,
    capacity_config_from_model,
    epics_df_from_models,
)
from models import ComputeResponse
from persistence import load_session, save_session

router = APIRouter()


def _mondays_for_quarter(quarter: int):
    from datetime import date
    start, end = get_quarter_dates(quarter)
    mondays = []
    d = start
    d += timedelta(days=(7 - d.weekday()) % 7)
    while d <= end:
        mondays.append(d)
        d += timedelta(weeks=1)
    return mondays, start, end


@router.post("/sessions/{session_id}/compute", response_model=ComputeResponse)
async def compute_session(session_id: str) -> ComputeResponse:
    session = load_session(session_id)

    capacity = capacity_config_from_model(session.capacity)
    epics_df = epics_df_from_models(session.epics)
    mondays, start, end = _mondays_for_quarter(session.quarter)

    df = build_output_table(epics_df, capacity, start, end)

    # Determine all week labels from the DataFrame
    from planzen.config import (
        OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_ESTIMATION,
        OUT_COL_OFF_ESTIMATE, OUT_COL_PRIORITY, OUT_COL_TOTAL_WEEKS,
    )
    non_week = {
        OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
        OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS, OUT_COL_OFF_ESTIMATE,
    }
    all_week_labels = [c for c in df.columns if c not in non_week]
    quarter_week_labels = [d.strftime("%b.%d") for d in mondays]
    has_overflow = len(all_week_labels) > len(quarter_week_labels)

    # Apply manual overrides (display-only post-processing)
    if session.manual_overrides:
        for _, row in df.iterrows():
            epic = str(row.get(OUT_COL_EPIC, ""))
            if epic in session.manual_overrides:
                for week_label, value in session.manual_overrides[epic].items():
                    if week_label in df.columns:
                        df.at[row.name, week_label] = value

    # Validate after applying overrides
    all_mondays = mondays
    if has_overflow:
        from datetime import timedelta as td
        overflow_start = end + td(weeks=1)
        overflow_end = overflow_start + td(weeks=12)
        day = overflow_start
        day += td(days=(7 - day.weekday()) % 7)
        while day <= overflow_end:
            all_mondays.append(day)
            day += td(weeks=1)

    violations = validate_allocation(df, capacity, all_mondays)

    rows = allocation_df_to_rows(df, all_week_labels, quarter_week_labels)

    return ComputeResponse(
        session_id=session_id,
        rows=rows,
        week_labels=all_week_labels,
        has_overflow=has_overflow,
        validation_errors=violations,
    )
