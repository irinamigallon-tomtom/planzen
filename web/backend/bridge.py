"""
Thin adapter layer: converts between JSON-serialisable Pydantic models and
the core planzen types (CapacityConfig, pandas DataFrames).
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from planzen.config import (
    COL_ALLOC_MODE,
    COL_BUDGET_BUCKET,
    COL_DEPENDS_ON,
    COL_EPIC,
    COL_ESTIMATION,
    COL_LINK,
    COL_MILESTONE,
    COL_PRIORITY,
    COL_TYPE,
    OUT_COL_BUDGET_BUCKET,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_OFF_ESTIMATE,
    OUT_COL_PRIORITY,
    OUT_COL_TOTAL_WEEKS,
)
from planzen.core_logic import CapacityConfig

from models import AllocationRow, CapacityConfigModel, EpicModel

_CURRENT_YEAR = datetime.now().year


def _label_to_date(label: str, reference_year: int = _CURRENT_YEAR) -> date:
    """
    Convert a week label like "Mar.30" to a date object.

    Tries current year; if the resulting date is in the past relative to
    the quarter start range, bumps to next year.
    """
    dt = datetime.strptime(f"{label}.{reference_year}", "%b.%d.%Y")
    return dt.date()


def _date_to_label(d: date) -> str:
    return d.strftime("%b.%d")


def capacity_config_from_model(model: CapacityConfigModel) -> CapacityConfig:
    """Build a CapacityConfig dataclass from a CapacityConfigModel."""
    eng_bruto_by_week: dict[date, float] | None = None
    eng_absence_by_week: dict[date, float] | None = None

    if model.eng_bruto_by_week:
        eng_bruto_by_week = {
            _label_to_date(label): value
            for label, value in model.eng_bruto_by_week.items()
        }
    if model.eng_absence_by_week:
        eng_absence_by_week = {
            _label_to_date(label): value
            for label, value in model.eng_absence_by_week.items()
        }

    return CapacityConfig(
        num_engineers=model.eng_bruto,
        num_managers=model.mgmt_capacity,
        eng_absence_per_week=model.eng_absence,
        mgmt_absence_per_week=model.mgmt_absence,
        eng_bruto_by_week=eng_bruto_by_week,
        eng_absence_by_week=eng_absence_by_week,
    )


def capacity_config_to_model(config: CapacityConfig, mondays: list[date]) -> CapacityConfigModel:
    """Extract a CapacityConfigModel from a CapacityConfig + list of week dates."""
    eng_bruto_by_week: dict[str, float] = {}
    eng_absence_by_week: dict[str, float] = {}

    if config.eng_bruto_by_week:
        eng_bruto_by_week = {
            _date_to_label(d): v for d, v in config.eng_bruto_by_week.items()
        }
    if config.eng_absence_by_week:
        eng_absence_by_week = {
            _date_to_label(d): v for d, v in config.eng_absence_by_week.items()
        }

    return CapacityConfigModel(
        eng_bruto=config.eng_bruto,
        eng_absence=config.eng_absence,
        mgmt_capacity=config.mgmt_capacity,
        mgmt_absence=config.mgmt_absence,
        eng_bruto_by_week=eng_bruto_by_week,
        eng_absence_by_week=eng_absence_by_week,
    )


def epics_df_from_models(epics: list[EpicModel]) -> pd.DataFrame:
    """Build a DataFrame with the correct column names from a list of EpicModel."""
    rows = []
    for epic in epics:
        rows.append({
            COL_EPIC: epic.epic_description,
            COL_ESTIMATION: epic.estimation,
            COL_BUDGET_BUCKET: epic.budget_bucket,
            COL_PRIORITY: epic.priority,
            COL_ALLOC_MODE: epic.allocation_mode,
            COL_LINK: epic.link,
            COL_TYPE: epic.type,
            COL_MILESTONE: epic.milestone,
            COL_DEPENDS_ON: epic.depends_on,
        })
    return pd.DataFrame(rows)


def allocation_df_to_rows(
    df: pd.DataFrame,
    week_labels: list[str],
    quarter_week_labels: list[str],
) -> list[AllocationRow]:
    """Serialise the output DataFrame to a list of AllocationRow."""
    non_week = {
        OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
        OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS, OUT_COL_OFF_ESTIMATE,
    }

    rows: list[AllocationRow] = []
    for _, row in df.iterrows():
        label = str(row[OUT_COL_EPIC])

        priority_val = row.get(OUT_COL_PRIORITY, None)
        try:
            priority = float(priority_val) if priority_val not in (None, "", float("nan")) else None
        except (TypeError, ValueError):
            priority = None

        estimation_val = row.get(OUT_COL_ESTIMATION, None)
        try:
            estimation = float(estimation_val) if estimation_val not in (None, "", float("nan")) else None
        except (TypeError, ValueError):
            estimation = None

        total_weeks_val = row.get(OUT_COL_TOTAL_WEEKS, None)
        try:
            total_weeks = float(total_weeks_val) if total_weeks_val not in (None, "", float("nan")) else None
        except (TypeError, ValueError):
            total_weeks = None

        off_estimate_val = row.get(OUT_COL_OFF_ESTIMATE, None)
        if off_estimate_val in (None, ""):
            off_estimate = None
        else:
            try:
                off_estimate = bool(off_estimate_val)
            except (TypeError, ValueError):
                off_estimate = None

        week_values: dict[str, float | bool | None] = {}
        for col in df.columns:
            if col in non_week:
                continue
            if col not in week_labels:
                continue
            val = row[col]
            if val is None or (isinstance(val, float) and pd.isna(val)):
                week_values[col] = None
            elif isinstance(val, bool):
                week_values[col] = val
            else:
                try:
                    week_values[col] = float(val)
                except (TypeError, ValueError):
                    week_values[col] = None

        rows.append(AllocationRow(
            label=label,
            budget_bucket=str(row.get(OUT_COL_BUDGET_BUCKET, "") or ""),
            priority=priority,
            estimation=estimation,
            total_weeks=total_weeks,
            off_estimate=off_estimate,
            week_values=week_values,
        ))
    return rows
