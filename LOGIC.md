The resulting table must fulfill these requirements:

One row per Epic. It's title will be the second column.
One row for Engineering capacity (bruto).
One row for Engineering absence.
One row for Engineering Net Capacity.
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
The total amount of capacity in a given Week (i.e. all capacities allocated in that Week-column over all Rows) cannot exceed the Engineering Net Capacity for that week.

## Capacity calculation

The user provides the number of engineers (E) and line managers (M). The unit throughout is **Person-Weeks (PW)**. Each person contributes exactly 1 PW of bruto capacity per week.

| Metric | Formula |
|---|---|
| Engineering Capacity (Bruto) | `E × 1 PW = E` |
| Engineering Absence | `E ÷ 12` |
| Engineering Net Capacity | `E − (E ÷ 12)` |
| Management Capacity | `M × 1 PW = M` |
| Management Absence | `M ÷ 12` |
| Management Net Capacity | `M − (M ÷ 12)` |

The factor of 1/12 represents the assumed fraction of working time lost to absence (e.g. holidays, sick leave).

See a description of the expected output table below:

| Budget Bucket   | Epic / Capacity Metric        | Priority   | Estimation   | Total Weeks   | 01.05   | 01.12   | 01.19   | 01.26   | 02.02   | ...   |
| --------------- | ----------------------------- | ---------- | ------------ | ------------- | ------- | ------- | ------- | ------- | ------- | ----- |
|                 | Engineering Capacity (Bruto)  |            |              |               | 5.0     | 5.0     | 5.0     | 5.0     | 5.0     | ...   |
|                 | Engineering Absence           |            |              |               | 0.4     | 0.4     | 0.4     | 0.4     | 0.4     | ...   |
|                 | Engineering Net Capacity      |            |              |               | 4.6     | 4.6     | 4.6     | 4.6     | 4.6     | ...   |
|                 | Management Capacity           |            |              |               | 2.0     | 2.0     | 2.0     | 2.0     | 2.0     | ...   |
|                 | Management Absence            |            |              |               | 0.2     | 0.2     | 0.2     | 0.2     | 0.2     | ...   |
|                 | Management Net Capacity       |            |              |               | 1.8     | 1.8     | 1.8     | 1.8     | 1.8     | ...   |
| --------------- | ----------------------------- | ---------- | ------------ | ------------- | ------- | ------- | ------- | ------- | ------- | ----- |
| Platform        | Auth & Identity Management    | 0          | 80.0         | 78.0          | 1.5     | 1.5     | 1.5     | 1.5     | 1.5     | ...   |
| Analytics       | Real-time Analytics           | 0          | 120.0        | 119.6         | 2.3     | 2.3     | 2.3     | 2.3     | 2.3     | ...   |
| Product         | Mobile App Redesign           | 1          | 100.0        | 98.8          | 1.9     | 1.9     | 1.9     | 1.9     | 1.9     | ...   |
| Platform        | API Gateway Optimization      | 1          | 60.0         | 59.8          | 1.1     | 1.1     | 1.1     | 1.1     | 1.1     | ...   |
| Analytics       | Data Quality Framework        | 2          | 90.0         | 89.7          | 1.7     | 1.7     | 1.7     | 1.7     | 1.7     | ...   |
| Total           | Weekly Allocation             |            |              |               | 8.5     | 8.5     | 8.5     | 8.5     | 8.5     | ...   |