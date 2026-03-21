The resulting table must fulfill these requirements:

One row per Epic. It's title will be the second column.
One row for Engineer capacity (bruto).
One row for Engineer absence.
One row for Engineer Net Capacity.
One row for Management capacity.
One row for Management absence.
One row for Management Net Capacity.
The first column is the Budget Bucket that Epic is allocated to.
One column for the Epic's Priority.
One column for the Epic's Estimated capacity ("Estimation").
In addition, a succession of columns, where each column corresponds to a week in 2026. The title of these columns is the date of the Monday in that week. 
The content of each such week-column shall be the capacity allocated in that week to a given Epic.
Each cell in a column may have a float number allocated to it, in 0.1 increments.
The total amount of capacity allocated over all weeks to a given Epic cannot exceed its Estimation.
The total amount of capacity in a given Week (i.e. all capacities allocated in that Week-column over all Rows) cannot exceed the Engineer Net Capacity for that week.
The user provides the quarter via CLI (e.g. -q 1). See the table below for quarters' running dates.
The allocation starts on the first week of the selected quarter. Capacities are allocated sequentially, that is, if capacity for one Epic has started in week "04.01", the following weeks must also have some capacity allocated to this epic, until they add up to the Estimation for that Epic.


## Mandatory checks

The total amount of capacity allocated over all weeks to a given Epic cannot exceed its Estimation.
The total amount of capacity in a given Week (i.e. all capacities allocated in that Week-column over all Rows) cannot exceed the total Engineer Net Capacity for that week.
No Epic has more than 2PW allocated per week. This makes sense because we want at most a tandem of 2 people working full time on something.

## 2026 Fiscal Quarters

| Quarter | Start Monday   |
|---------|----------------|
| Q1      | 2025-12-29     |
| Q2      | 2026-03-30     |
| Q3      | 2026-06-29     |
| Q4      | 2026-09-28     |

## Capacity calculation

The user provides the number of engineers (E) and line managers (M). The unit throughout is **Person-Weeks (PW)**. Each person contributes exactly 1 PW of bruto capacity per week.

Absence is derived from a combined total of **37 days per year** (30 vacation + 7 sick days), distributed over 52 weeks = **0.71 days/week per person** = **≈ 0.142 PW/week per person** (÷ 5 working days/week).

| Metric | Formula |
|---|---|
| Engineer Capacity (Bruto) | `E × 1 PW = E PW` |
| Engineer Absence | `E × 0.142 PW` (= E × 0.71 days ÷ 5; 37 days/year ÷ 52 weeks) |
| Engineer Net Capacity | `Engineer Capacity - Engineer Absence` |
| Management Capacity | `M × 1 PW = M` |
| Management Absence | `M × 0.142 PW` |
| Management Net Capacity | `Management Capacity - Management Absence` |

## Expected output layout

See a description of the expected output table below:

| Budget Bucket   | Epic / Capacity Metric        | Priority   | Estimation   | Total Weeks   | "01.05"   | "01.12"  | ...   |
| --------------- | ----------------------------- | ---------- | ------------ | ------------- | ------- | ------- | -------  |
|                 | Engineer Capacity (Bruto)  |            |              |               | 5.0     | 5.0     | ...   |
|                 | Engineer Absence           |            |              |               | 0.7     | 0.7     | ...   |
|                 | Engineer Net Capacity      |            |              |               | 4.3     | 4.3     | ...   |
|                 | Management Capacity           |            |              |               | 2.0     | 2.0     | ...   |
|                 | Management Absence            |            |              |               | 0.3     | 0.3     | ...   |
|                 | Management Net Capacity       |            |              |               | 1.7     | 1.7     | ...   |
| --------------- | ----------------------------- | ---------- | ------------ | ------------- | ------- | ------- | ------- | 
| Platform        | Auth & Identity Management    | 0          | 80.0         | 78.0          | 1.5     | 1.5     | ...   |
| Analytics       | Real-time Analytics           | 0          | 120.0        | 119.6         | 2.3     | 2.3     | ...   |
| Product         | Mobile App Redesign           | 1          | 100.0        | 98.8          | 1.9     | 1.9     | ...   |
| Platform        | API Gateway Optimization      | 1          | 60.0         | 59.8          | 1.1     | 1.1     | ...   |
| Analytics       | Data Quality Framework        | 2          | 90.0         | 89.7          | 1.7     | 1.7     | ...   |
| Total           | Weekly Allocation             |            |              |               | 8.5     | 8.5     | ...   |