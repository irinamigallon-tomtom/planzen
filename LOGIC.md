The resulting table must fulfill these requirements:

One row per Epic. It's title will be the second column.
One row for Engineering capacity (bruto).
One row for Engineering absence.
One row for Management capacity.
One row for Management absence.
One row for Engineering Net Capacity.
The first column is the Budget Bucket that Epic is allocated to.
One column for the Epic's Priority.
One column for the Epic's Estimated capacity ("Estimation").
In addition, a succession of columns, where each column corresponds to a week in 2026. The title of these columns is the date of the Monday in that week. 
The content of each such week-column shall be the capacity allocated in that week to a given Epic.
Each cell in a column may have a float number allocated to it, in 0.1 increments.
The total amount of capacity allocated over all weeks to a given Epic cannot exceed its Estimation.
The total amount of capacity in a given Week (i.e. all capacities allocated in that Week-column over all Rows) cannot exceed the Engineering Net Capacity for that week.

See a description of the expected output table below:

| Budget Bucket   | Epic / Capacity Metric        | Priority   | Estimation   | Total Weeks   | 01.05   | 01.12   | 01.19   | 01.26   | 02.02   | ...   |
| --------------- | ----------------------------- | ---------- | ------------ | ------------- | ------- | ------- | ------- | ------- | ------- | ----- |
|                 | Engineering Capacity (Bruto)  |            |              |               | 40.0    | 40.0    | 40.0    | 40.0    | 40.0    | ...   |
|                 | Engineering Absence           |            |              |               | 4.0     | 4.0     | 4.0     | 4.0     | 4.0     | ...   |
|                 | Engineering Net Capacity      |            |              |               | 36.0    | 36.0    | 36.0    | 36.0    | 36.0    | ...   |
|                 | Management Capacity           |            |              |               | 10.0    | 10.0    | 10.0    | 10.0    | 10.0    | ...   |
|                 | Management Absence            |            |              |               | 1.0     | 1.0     | 1.0     | 1.0     | 1.0     | ...   |
| --------------- | ----------------------------- | ---------- | ------------ | ------------- | ------- | ------- | ------- | ------- | ------- | ----- |
| Platform        | Auth & Identity Management    | 0          | 80.0         | 80.0          | 6.2     | 6.2     | 6.2     | 6.2     | 6.2     | ...   |
| Analytics       | Real-time Analytics           | 0          | 120.0        | 119.6         | 9.2     | 9.2     | 9.2     | 9.2     | 9.2     | ...   |
| Product         | Mobile App Redesign           | 1          | 100.0        | 100.1         | 7.7     | 7.7     | 7.7     | 7.7     | 7.7     | ...   |
| Platform        | API Gateway Optimization      | 1          | 60.0         | 59.8          | 4.6     | 4.6     | 4.6     | 4.6     | 4.6     | ...   |
| Analytics       | Data Quality Framework        | 2          | 90.0         | 89.7          | 6.9     | 6.9     | 6.9     | 6.9     | 6.9     | ...   |
| Total           | Weekly Allocation             |            |              |               | 34.6    | 34.6    | 34.6    | 34.6    | 34.6    | ...   |