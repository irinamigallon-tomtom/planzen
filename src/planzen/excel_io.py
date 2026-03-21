"""
Excel I/O for planzen.

Reads the input plan file and writes the output allocation table.
All file operations are isolated here; core_logic stays pure.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from planzen.config import (
    COL_BUDGET_BUCKET,
    COL_EPIC,
    COL_ESTIMATION,
    COL_MILESTONE,
    COL_PRIORITY,
)

REQUIRED_INPUT_COLUMNS = {
    COL_EPIC,
    COL_ESTIMATION,
    COL_BUDGET_BUCKET,
    COL_PRIORITY,
    COL_MILESTONE,
}


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
    """Write the output allocation table to an Excel file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Allocation")
