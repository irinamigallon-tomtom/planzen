export interface CapacityConfig {
  eng_bruto: number;
  eng_absence: number;
  mgmt_capacity: number;
  mgmt_absence: number;
  eng_bruto_by_week: Record<string, number>;
  eng_absence_by_week: Record<string, number>;
}

export interface Epic {
  epic_description: string;
  estimation: number;
  budget_bucket: string;
  priority: number;
  allocation_mode: 'Sprint' | 'Uniform' | 'Gaps';
  link: string;
  type: string;
  milestone: string;
  depends_on: string;
}

export interface SessionSummary {
  session_id: string;
  filename: string;
  quarter: number;
}

export interface SessionState extends SessionSummary {
  capacity: CapacityConfig;
  epics: Epic[];
  manual_overrides: Record<string, Record<string, number>>;
}

export interface AllocationRow {
  label: string;
  budget_bucket: string;
  priority: number | null;
  estimation: number | null;
  total_weeks: number | null;
  off_estimate: boolean | null;
  week_values: Record<string, number | boolean | null>;
}

export interface ComputeResponse {
  session_id: string;
  rows: AllocationRow[];
  week_labels: string[];
  has_overflow: boolean;
  validation_errors: string[];
}
