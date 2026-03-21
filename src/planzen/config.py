"""
Configuration constants for planzen.
"""

from datetime import date, timedelta

# Input column names expected in the source Excel file
# Required columns
COL_EPIC = "Epic Description"
COL_ESTIMATION = "Estimation"
COL_BUDGET_BUCKET = "Budget Bucket"
COL_TYPE = "Type"
COL_LINK = "Link"
COL_PRIORITY = "Priority"

# Optional input columns (used when present)
COL_MILESTONE = "Milestone"

# Team config rows — appear at the top of the epics sheet before the epic data.
# The Estimation column holds the numeric value for each config row.
TEAM_LABEL_ENGINEERS      = "Engineer Bruto Capacity"
TEAM_LABEL_MANAGERS       = "Management Bruto Capacity"
TEAM_LABEL_ENG_ABSENCE    = "Engineer Absence (days)"   # optional
TEAM_LABEL_MGMT_ABSENCE   = "Manager Absence (days)"    # optional

TEAM_CONFIG_LABELS = {
    TEAM_LABEL_ENGINEERS,
    TEAM_LABEL_MANAGERS,
    TEAM_LABEL_ENG_ABSENCE,
    TEAM_LABEL_MGMT_ABSENCE,
}

# Output table column labels
OUT_COL_BUDGET_BUCKET = "Budget Bucket"
OUT_COL_EPIC = "Epic / Capacity Metric"
OUT_COL_PRIORITY = "Priority"
OUT_COL_ESTIMATION = "Estimation"
OUT_COL_TOTAL_WEEKS = "Total Weeks"

# Capacity header row labels
LABEL_ENG_BRUTO = "Engineer Capacity (Bruto)"
LABEL_ENG_ABSENCE = "Engineer Absence"
LABEL_ENG_NET = "Engineer Net Capacity"
LABEL_MGMT_CAPACITY = "Management Capacity"
LABEL_MGMT_ABSENCE = "Management Absence"
LABEL_MGMT_NET = "Management Net Capacity"
LABEL_TOTAL_ROW = "Weekly Allocation"
LABEL_TOTAL_BUCKET = "Total"

ABSENCE_DAYS_PER_YEAR = 37
WORKING_WEEKS_PER_YEAR = 52
WORKING_DAYS_PER_WEEK = 5
ABSENCE_PW_PER_PERSON: float = (
    ABSENCE_DAYS_PER_YEAR / WORKING_WEEKS_PER_YEAR / WORKING_DAYS_PER_WEEK
)  # ≈ 0.1423

# 2026 Fiscal Quarters: (start_monday, end_monday).
# Each quarter spans exactly 13 Mondays (end = start + 12 weeks).
_Q_STARTS: dict[int, date] = {
    1: date(2025, 12, 29),
    2: date(2026, 3, 30),
    3: date(2026, 6, 29),
    4: date(2026, 9, 28),
}
FISCAL_QUARTERS: dict[int, tuple[date, date]] = {
    q: (start, start + timedelta(weeks=12))
    for q, start in _Q_STARTS.items()
}
