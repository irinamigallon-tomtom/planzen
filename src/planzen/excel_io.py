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
    COL_MILESTONE,
    COL_PRIORITY,
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
    COL_PRIORITY,
    COL_MILESTONE,
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


def read_plan(path: Path) -> pd.DataFrame:
    """
    Read the input Excel file and return a DataFrame with the plan rows.

    Raises
    ------
    ValueError
        If any required columns are missing from the file.
    """
    df = pd.read_excel(path)
    missing = REQUIRED_INPUT_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Input file is missing required columns: {sorted(missing)}"
        )
    return df[list(REQUIRED_INPUT_COLUMNS)]


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
