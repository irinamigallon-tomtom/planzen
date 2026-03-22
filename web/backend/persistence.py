"""
Session persistence: save/load SessionState as JSON files in tmp/sessions/.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from models import SessionState

_DEFAULT_SESSION_DIR = Path(__file__).parents[2] / "tmp" / "sessions"


def _session_dir() -> Path:
    d = Path(os.environ.get("PLANZEN_SESSION_DIR", _DEFAULT_SESSION_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_path(session_id: str) -> Path:
    return _session_dir() / f"{session_id}.json"


def new_session_id() -> str:
    return str(uuid4())


def save_session(state: SessionState) -> None:
    path = _session_path(state.session_id)
    path.write_text(state.model_dump_json(), encoding="utf-8")


def load_session(session_id: str) -> SessionState:
    path = _session_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionState(**data)


def list_sessions() -> list[SessionState]:
    sessions: list[SessionState] = []
    for p in _session_dir().glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            sessions.append(SessionState(**data))
        except Exception:
            pass
    return sessions


def delete_session(session_id: str) -> None:
    path = _session_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    path.unlink()
