"""
Routes for session management.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

# Ensure src/ is on the path (also set in main.py, but routes may be imported standalone)
_SRC = Path(__file__).parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from planzen.excel_io import read_input, validate_input_file

from bridge import capacity_config_to_model, epics_df_from_models
from models import CapacityConfigModel, EpicModel, SessionState
from persistence import delete_session, list_sessions, load_session, new_session_id, save_session
from planzen.core_logic import get_quarter_dates

router = APIRouter()


@router.post("/sessions/upload", response_model=SessionState)
async def upload_session(
    file: UploadFile = File(...),
    quarter: int = Form(...),
) -> SessionState:
    suffix = Path(file.filename or "upload.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        errors = validate_input_file(tmp_path, quarter)
        if errors:
            raise HTTPException(status_code=422, detail=errors)

        epics_df, capacity_config = read_input(tmp_path, quarter)
    finally:
        tmp_path.unlink(missing_ok=True)

    start, end = get_quarter_dates(quarter)
    from datetime import timedelta
    mondays = []
    d = start
    from datetime import date
    d += __import__("datetime").timedelta(days=(7 - d.weekday()) % 7)
    while d <= end:
        mondays.append(d)
        d += __import__("datetime").timedelta(weeks=1)

    capacity_model = capacity_config_to_model(capacity_config, mondays)

    epics: list[EpicModel] = []
    for _, row in epics_df.iterrows():
        from planzen.config import (
            COL_ALLOC_MODE, COL_BUDGET_BUCKET, COL_EPIC, COL_ESTIMATION,
            COL_LINK, COL_MILESTONE, COL_PRIORITY, COL_TYPE,
        )
        import pandas as pd
        epics.append(EpicModel(
            epic_description=str(row[COL_EPIC]),
            estimation=float(row[COL_ESTIMATION]),
            budget_bucket=str(row.get(COL_BUDGET_BUCKET, "") or ""),
            priority=float(row[COL_PRIORITY]),
            allocation_mode=str(row[COL_ALLOC_MODE]) if COL_ALLOC_MODE in row.index and pd.notna(row[COL_ALLOC_MODE]) else "Sprint",
            link=str(row[COL_LINK]) if COL_LINK in row.index and pd.notna(row[COL_LINK]) else "",
            type=str(row[COL_TYPE]) if COL_TYPE in row.index and pd.notna(row[COL_TYPE]) else "",
            milestone=str(row[COL_MILESTONE]) if COL_MILESTONE in row.index and pd.notna(row[COL_MILESTONE]) else "",
        ))

    session = SessionState(
        session_id=new_session_id(),
        filename=file.filename or "upload.xlsx",
        quarter=quarter,
        capacity=capacity_model,
        epics=epics,
    )
    save_session(session)
    return session


@router.get("/sessions", response_model=list[dict])
async def get_sessions() -> list[dict]:
    sessions = list_sessions()
    return [
        {"session_id": s.session_id, "filename": s.filename, "quarter": s.quarter}
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    return load_session(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def remove_session(session_id: str) -> None:
    delete_session(session_id)


@router.put("/sessions/{session_id}/capacity", response_model=SessionState)
async def update_capacity(session_id: str, capacity: CapacityConfigModel) -> SessionState:
    session = load_session(session_id)
    session.capacity = capacity
    save_session(session)
    return session


@router.put("/sessions/{session_id}/epics", response_model=SessionState)
async def update_epics(session_id: str, epics: list[EpicModel]) -> SessionState:
    session = load_session(session_id)
    session.epics = epics
    save_session(session)
    return session


@router.patch("/sessions/{session_id}/overrides", response_model=SessionState)
async def update_overrides(
    session_id: str, overrides: dict[str, dict[str, float]]
) -> SessionState:
    session = load_session(session_id)
    session.manual_overrides = overrides
    save_session(session)
    return session
