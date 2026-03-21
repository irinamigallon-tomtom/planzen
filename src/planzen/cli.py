"""
CLI entrypoint for planzen.

Usage:
    uv run planzen run INPUT_FILE OUTPUT_FILE [OPTIONS]
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from planzen.core_logic import CapacityConfig, build_output_table
from planzen.excel_io import read_plan, write_output

app = typer.Typer(help="planzen — weekly capacity allocation tool.")


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="Path to the input Excel plan file."),
    output_file: Path = typer.Argument(..., help="Path for the output Excel file."),
    start: str = typer.Option(..., help="Start date (YYYY-MM-DD)."),
    end: str = typer.Option(..., help="End date (YYYY-MM-DD)."),
    eng_bruto: float = typer.Option(40.0, help="Weekly engineering capacity (bruto)."),
    eng_absence: float = typer.Option(4.0, help="Weekly engineering absence."),
    mgmt_capacity: float = typer.Option(10.0, help="Weekly management capacity."),
    mgmt_absence: float = typer.Option(1.0, help="Weekly management absence."),
) -> None:
    """Process an input plan and write the allocation table to OUTPUT_FILE."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    epics_df = read_plan(input_file)
    capacity = CapacityConfig(
        eng_bruto=eng_bruto,
        eng_absence=eng_absence,
        mgmt_capacity=mgmt_capacity,
        mgmt_absence=mgmt_absence,
    )
    output_df = build_output_table(epics_df, capacity, start_date, end_date)
    write_output(output_df, output_file)
    typer.echo(f"Output written to {output_file}")


def main() -> None:
    app()
