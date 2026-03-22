"""
Pydantic v2 request/response models for the planzen API.
"""
from __future__ import annotations

from pydantic import BaseModel


class CapacityConfigModel(BaseModel):
    eng_bruto: float
    eng_absence: float  # PW/week
    mgmt_capacity: float
    mgmt_absence: float  # PW/week
    # Optional per-week overrides: week label (e.g. "Mar.30") → float
    eng_bruto_by_week: dict[str, float] = {}
    eng_absence_by_week: dict[str, float] = {}


class EpicModel(BaseModel):
    epic_description: str
    estimation: float
    budget_bucket: str
    priority: float
    allocation_mode: str = "Sprint"
    link: str = ""
    type: str = ""
    milestone: str = ""


class SessionState(BaseModel):
    session_id: str
    filename: str
    quarter: int
    capacity: CapacityConfigModel
    epics: list[EpicModel]
    manual_overrides: dict[str, dict[str, float]] = {}  # epic_description → week_label → PW


class AllocationRow(BaseModel):
    label: str          # Epic Description or capacity row label
    budget_bucket: str = ""
    priority: float | None = None
    estimation: float | None = None
    total_weeks: float | None = None
    off_estimate: bool | None = None
    week_values: dict[str, float | bool | None] = {}  # week_label → value


class ComputeResponse(BaseModel):
    session_id: str
    rows: list[AllocationRow]
    week_labels: list[str]
    has_overflow: bool
    validation_errors: list[str] = []
