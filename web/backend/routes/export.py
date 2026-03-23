"""
Export route: builds output tables and returns a zip of two Excel files.
"""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from planzen.core_logic import build_output_table, get_quarter_dates
from planzen.excel_io import write_output, write_output_with_formulas
from planzen.config import (
    OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_ESTIMATION,
    OUT_COL_OFF_ESTIMATE, OUT_COL_PRIORITY, OUT_COL_TOTAL_WEEKS,
)

from bridge import capacity_config_from_model, epics_df_from_models
from persistence import load_session

router = APIRouter()

_TMP_DIR = Path(__file__).parents[3] / "tmp"
_NON_WEEK = {
    OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
    OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS, OUT_COL_OFF_ESTIMATE,
}


def _mondays_for_quarter(quarter: int):
    start, end = get_quarter_dates(quarter)
    mondays = []
    d = start
    d += timedelta(days=(7 - d.weekday()) % 7)
    while d <= end:
        mondays.append(d)
        d += timedelta(weeks=1)
    return mondays, start, end


@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str) -> StreamingResponse:
    session = load_session(session_id)

    capacity = capacity_config_from_model(session.capacity)
    epics_df = epics_df_from_models(session.epics)
    mondays, start, end = _mondays_for_quarter(session.quarter)

    df = build_output_table(epics_df, capacity, start, end)

    # Apply manual overrides
    if session.manual_overrides:
        for _, row in df.iterrows():
            epic = str(row.get(OUT_COL_EPIC, ""))
            if epic in session.manual_overrides:
                for week_label, value in session.manual_overrides[epic].items():
                    if week_label in df.columns:
                        df.at[row.name, week_label] = value

    all_week_labels = [c for c in df.columns if c not in _NON_WEEK]
    n_base_weeks = len(mondays)

    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    values_path = _TMP_DIR / f"{session_id}_values.xlsx"
    formulas_path = _TMP_DIR / f"{session_id}_formulas.xlsx"

    write_output(df, values_path)
    write_output_with_formulas(df, formulas_path, n_base_weeks=n_base_weeks)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(session.filename).stem
    zip_name = f"output_{base_name}_{timestamp}.zip"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(values_path, arcname=f"output_{base_name}_{timestamp}_values.xlsx")
        zf.write(formulas_path, arcname=f"output_{base_name}_{timestamp}_formulas.xlsx")
    buf.seek(0)

    values_path.unlink(missing_ok=True)
    formulas_path.unlink(missing_ok=True)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )
