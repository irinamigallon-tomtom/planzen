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
COL_ALLOC_MODE = "Allocation Mode"    # optional per-epic; blank → Sprint

# Allocation modes
ALLOC_MODE_SPRINT  = "Sprint"         # default: allocate up to MAX_WEEKLY_ALLOC_PW, sequential
ALLOC_MODE_UNIFORM = "Uniform"        # spread estimation evenly across weeks, sequential
ALLOC_MODE_GAPS    = "Gaps"   # Sprint rate but no sequential minimum

ALLOC_MODE_DEFAULT = ALLOC_MODE_SPRINT
VALID_ALLOC_MODES: frozenset[str] = frozenset({
    ALLOC_MODE_SPRINT, ALLOC_MODE_UNIFORM, ALLOC_MODE_GAPS,
})

# Maximum PW a single epic may receive in one week (Sprint / Gaps).
# Represents at most a tandem of 2 people working full-time.  Configurable here.
MAX_WEEKLY_ALLOC_PW: float = 2.0

# Team config rows — identified by their label in the Budget Bucket column (or
# Type column as a fallback). The Estimation column holds the numeric value.
# Labels match the output row labels where applicable.
TEAM_LABEL_ENGINEERS      = "Engineer Capacity (Bruto)"    # = LABEL_ENG_BRUTO
TEAM_LABEL_NUM_ENGINEERS  = "Num Engineers"                # headcount; derives eng_bruto when Bruto row absent
TEAM_LABEL_MANAGERS       = "Management Capacity (Bruto)"  # = LABEL_MGMT_CAPACITY; optional, default 1.0
TEAM_LABEL_ENG_ABSENCE    = "Engineer Absence"             # = LABEL_ENG_ABSENCE; optional
TEAM_LABEL_MGMT_ABSENCE   = "Management Absence"           # = LABEL_MGMT_ABSENCE; optional

DEFAULT_MGMT_CAPACITY_PW: float = 1.0  # PW/week when no management config row is found

TEAM_CONFIG_LABELS = {
    TEAM_LABEL_ENGINEERS,
    TEAM_LABEL_NUM_ENGINEERS,
    TEAM_LABEL_MANAGERS,
    TEAM_LABEL_ENG_ABSENCE,
    TEAM_LABEL_MGMT_ABSENCE,
}

# Output table column labels
OUT_COL_BUDGET_BUCKET = "Budget Bucket"
OUT_COL_EPIC = "Epic Description"
OUT_COL_PRIORITY = "Priority"
OUT_COL_ESTIMATION = "Estimation"
OUT_COL_TOTAL_WEEKS = "Total Weeks"

# Capacity header row labels
LABEL_ENG_BRUTO = "Engineer Capacity (Bruto)"
LABEL_ENG_ABSENCE = "Engineer Absence"
LABEL_ENG_NET = "Engineer Net Capacity"
LABEL_MGMT_CAPACITY = "Management Capacity (Bruto)"
LABEL_MGMT_ABSENCE = "Management Absence"
LABEL_MGMT_NET = "Management Net Capacity"
LABEL_TOTAL_ROW = "Weekly Allocation"
LABEL_TOTAL_BUCKET = "Total"
LABEL_CAPACITY_ALERT_ROW = "Off Capacity"

OUT_COL_OFF_ESTIMATE = "Off Estimate"

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
