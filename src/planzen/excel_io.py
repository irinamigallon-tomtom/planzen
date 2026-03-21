"""
Excel I/O for planzen.

Reads the input plan file and writes the output allocation table.
All file operations are isolated here; core_logic stays pure.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

from planzen.config import (
    COL_BUDGET_BUCKET,
    COL_EPIC,
    COL_ESTIMATION,
    COL_LINK,
    COL_PRIORITY,
    COL_TYPE,
    TEAM_CONFIG_LABELS,
    TEAM_LABEL_ENG_ABSENCE,
    TEAM_LABEL_ENGINEERS,
    TEAM_LABEL_MGMT_ABSENCE,
    TEAM_LABEL_MANAGERS,
    LABEL_ENG_ABSENCE,
    LABEL_ENG_BRUTO,
    LABEL_ENG_NET,
    LABEL_MGMT_ABSENCE,
    LABEL_MGMT_CAPACITY,
    LABEL_MGMT_NET,
    LABEL_TOTAL_ROW,
    OUT_COL_BUDGET_BUCKET,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_PRIORITY,
    OUT_COL_TOTAL_WEEKS,
)

REQUIRED_INPUT_COLUMNS = {
    COL_EPIC,
    COL_ESTIMATION,
    COL_BUDGET_BUCKET,
    COL_TYPE,
    COL_LINK,
    COL_PRIORITY,
}

_NON_WEEK_COLS = {
    OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
    OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS,
}

_CAPACITY_LABELS = {
    LABEL_ENG_BRUTO, LABEL_ENG_ABSENCE, LABEL_ENG_NET,
    LABEL_MGMT_CAPACITY, LABEL_MGMT_ABSENCE, LABEL_MGMT_NET,
    LABEL_TOTAL_ROW,
}


def formulas_path(path: Path) -> Path:
    """Return the sibling path for the formulas variant of an output file."""
    return path.with_stem(path.stem + "_formulas")


def read_input(path: Path) -> tuple[
    pd.DataFrame,   # epics
    float,          # num_engineers
    float,          # num_managers
    float | None,   # eng_absence_days (total for quarter, or None → use default)
    float | None,   # mgmt_absence_days (total for quarter, or None → use default)
]:
    """
    Read the input Excel file and return epics plus team capacity config.

    The sheet must begin with team config rows in columns A/B before the epic
    data.  Recognised config labels (in the ``Epic Description`` column):

    - ``Engineer Bruto Capacity``  *(required)*
    - ``Management Bruto Capacity`` *(required)*
    - ``Engineer Absence (days)``  *(optional — total days for the quarter)*
    - ``Manager Absence (days)``   *(optional — total days for the quarter)*

    Config rows are stripped before the epic DataFrame is returned.  The epic
    rows must contain all required columns; column order and extra columns are
    preserved.

    Raises
    ------
    ValueError
        If required config rows or epic columns are missing.
    """
    df = pd.read_excel(path)

    if COL_EPIC not in df.columns or COL_ESTIMATION not in df.columns:
        raise ValueError(
            f"Input file must have '{COL_EPIC}' and '{COL_ESTIMATION}' columns."
        )

    # --- extract team config rows ---
    config_mask = df[COL_EPIC].isin(TEAM_CONFIG_LABELS)
    config_df = df[config_mask].set_index(COL_EPIC)[COL_ESTIMATION]

    if TEAM_LABEL_ENGINEERS not in config_df.index:
        raise ValueError(
            f"Input file missing required config row: '{TEAM_LABEL_ENGINEERS}'"
        )
    if TEAM_LABEL_MANAGERS not in config_df.index:
        raise ValueError(
            f"Input file missing required config row: '{TEAM_LABEL_MANAGERS}'"
        )

    num_engineers: float = float(config_df[TEAM_LABEL_ENGINEERS])
    num_managers: float  = float(config_df[TEAM_LABEL_MANAGERS])
    eng_absence_days: float | None = (
        float(config_df[TEAM_LABEL_ENG_ABSENCE])
        if TEAM_LABEL_ENG_ABSENCE in config_df.index
        and pd.notna(config_df[TEAM_LABEL_ENG_ABSENCE])
        else None
    )
    mgmt_absence_days: float | None = (
        float(config_df[TEAM_LABEL_MGMT_ABSENCE])
        if TEAM_LABEL_MGMT_ABSENCE in config_df.index
        and pd.notna(config_df[TEAM_LABEL_MGMT_ABSENCE])
        else None
    )

    # --- epic rows (everything that isn't a config row) ---
    epics_df = df[~config_mask].reset_index(drop=True)

    missing = REQUIRED_INPUT_COLUMNS - set(epics_df.columns)
    if missing:
        raise ValueError(
            f"Input file is missing required columns: {sorted(missing)}"
        )

    return epics_df, num_engineers, num_managers, eng_absence_days, mgmt_absence_days


def write_output(df: pd.DataFrame, path: Path) -> None:
    """Write the output allocation table to an Excel file (values only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Allocation")


def write_output_with_formulas(df: pd.DataFrame, path: Path) -> None:
    """
    Write the output allocation table to an Excel file with formulas for
    calculated fields:

    - Engineer Net Capacity row: ``=<bruto_cell>-<absence_cell>`` per week
    - Management Net Capacity row: same pattern
    - Total Weeks column (epic rows): ``=SUM(<first_week>:<last_week>)``
    - Weekly Allocation row: ``=SUM(<first_epic>:<last_epic>)`` per week
    """
    # Write values first, then reopen to replace calculated cells with formulas.
    write_output(df, path)
    wb = openpyxl.load_workbook(path)
    ws = wb.active

    col_names = list(df.columns)
    week_col_indices = [
        col_names.index(c) + 1
        for c in col_names if c not in _NON_WEEK_COLS
    ]
    total_weeks_col_idx = col_names.index(OUT_COL_TOTAL_WEEKS) + 1

    # Excel row = DataFrame index + 2  (0-indexed df + 1 for header + 1 for 1-based)
    labels = list(df[OUT_COL_EPIC])

    def excel_row(label: str) -> int:
        return labels.index(label) + 2

    r_eng_bruto   = excel_row(LABEL_ENG_BRUTO)
    r_eng_absence = excel_row(LABEL_ENG_ABSENCE)
    r_eng_net     = excel_row(LABEL_ENG_NET)
    r_mgmt_cap    = excel_row(LABEL_MGMT_CAPACITY)
    r_mgmt_absence = excel_row(LABEL_MGMT_ABSENCE)
    r_mgmt_net    = excel_row(LABEL_MGMT_NET)
    r_total       = excel_row(LABEL_TOTAL_ROW)

    epic_excel_rows = [
        i + 2 for i, lbl in enumerate(labels) if lbl not in _CAPACITY_LABELS
    ]
    first_week_letter = get_column_letter(week_col_indices[0])
    last_week_letter  = get_column_letter(week_col_indices[-1])
    first_epic_row = epic_excel_rows[0]
    last_epic_row  = epic_excel_rows[-1]

    # Engineer Net Capacity: =<bruto> - <absence>
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_eng_net, ci).value = f"={cl}{r_eng_bruto}-{cl}{r_eng_absence}"

    # Management Net Capacity: =<mgmt_cap> - <mgmt_absence>
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_mgmt_net, ci).value = f"={cl}{r_mgmt_cap}-{cl}{r_mgmt_absence}"

    # Total Weeks for each epic: =SUM(<first_week_col><row>:<last_week_col><row>)
    for er in epic_excel_rows:
        ws.cell(er, total_weeks_col_idx).value = (
            f"=SUM({first_week_letter}{er}:{last_week_letter}{er})"
        )

    # Weekly Allocation row: =SUM(<col><first_epic>:<col><last_epic>)
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_total, ci).value = (
            f"=SUM({cl}{first_epic_row}:{cl}{last_epic_row})"
        )

    wb.save(path)
