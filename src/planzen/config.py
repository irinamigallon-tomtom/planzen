"""
Configuration constants for planzen.
"""

# Input column names expected in the source Excel file
COL_EPIC = "Epics"
COL_ESTIMATION = "Estimation"
COL_BUDGET_BUCKET = "Budget Bucket"
COL_PRIORITY = "Priority"
COL_MILESTONE = "Milestone"

# Output table column labels
OUT_COL_BUDGET_BUCKET = "Budget Bucket"
OUT_COL_EPIC = "Epic / Capacity Metric"
OUT_COL_PRIORITY = "Priority"
OUT_COL_ESTIMATION = "Estimation"
OUT_COL_TOTAL_WEEKS = "Total Weeks"

# Capacity header row labels
LABEL_ENG_BRUTO = "Engineering Capacity (Bruto)"
LABEL_ENG_ABSENCE = "Engineering Absence"
LABEL_ENG_NET = "Engineering Net Capacity"
LABEL_MGMT_CAPACITY = "Management Capacity"
LABEL_MGMT_ABSENCE = "Management Absence"
LABEL_MGMT_NET = "Management Net Capacity"
LABEL_TOTAL_ROW = "Weekly Allocation"
LABEL_TOTAL_BUCKET = "Total"

# Absence model: 37 days/year (30 vacation + 7 sick) distributed over 52 weeks
# = 0.71 days/week per person = 0.142 PW/person/week (÷ 5 working days/week)
ABSENCE_DAYS_PER_YEAR = 37
WORKING_WEEKS_PER_YEAR = 52
WORKING_DAYS_PER_WEEK = 5
ABSENCE_PW_PER_PERSON: float = (
    ABSENCE_DAYS_PER_YEAR / WORKING_WEEKS_PER_YEAR / WORKING_DAYS_PER_WEEK
)  # ≈ 0.1423
