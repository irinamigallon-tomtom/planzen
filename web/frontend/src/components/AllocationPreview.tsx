import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, CellValueChangedEvent } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community';
import { updateOverrides } from '../api/client';
import type { ComputeResponse, AllocationRow } from '../types';

ModuleRegistry.registerModules([AllCommunityModule]);

interface AllocationPreviewProps {
  sessionId: string;
  computeResponse: ComputeResponse | null;
  /** Existing overrides from the saved session — used to initialise state and style overridden cells. */
  initialOverrides: Record<string, Record<string, number>>;
  onOverrideChanged: () => void;
}

const CAPACITY_LABELS = new Set([
  'Engineer Capacity (Bruto)',
  'Engineer Absence',
  'Engineer Net Capacity',
  'Management Capacity (Bruto)',
  'Management Absence',
  'Management Net Capacity',
]);

const BUDGET_BUCKET_COLORS: Record<string, string> = {
  'Self-Service ML EV Range - Phase 1': '#548235',
  'Quality improvements through ML/AI experimentation': '#C6EFCE',
  'Maintenance & Release': '#B4C6E7',
  'Security & Compliance': '#D9D2E9',
  'Customer Support': '#FFC7CE',
  'Critical Technical Debt': '#FCE4D6',
  'Critical Product Debt': '#FFF2CC',
  'Critical Customer Commitments': '#F8CBAD',
};

const OFF_STYLE = { background: '#FFC7CE', color: '#9C0006' };
// Editable epic cells get a subtle blue tint; overridden cells get amber.
const EDITABLE_STYLE = { background: '#EFF6FF', cursor: 'text' };
const OVERRIDDEN_STYLE = { background: '#FEF3C7', cursor: 'text' };

function isEpicRow(row: AllocationRow): boolean {
  return (
    !CAPACITY_LABELS.has(row.label) &&
    row.label !== 'Weekly Allocation' &&
    row.label !== 'Off Capacity'
  );
}

type RowDataItem = {
  label: string;
  budget_bucket: string;
  priority: number | null;
  estimation: number | null;
  total_weeks: number | null;
  off_estimate: boolean | null;
  _isEpic: boolean;
  _isOffCapacity: boolean;
  [key: string]: unknown;
};

export function AllocationPreview({
  sessionId,
  computeResponse,
  initialOverrides,
  onOverrideChanged,
}: AllocationPreviewProps) {
  const [overrides, setOverrides] = useState<Record<string, Record<string, number>>>(initialOverrides);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // When the session changes (e.g. user loads a different session), sync saved overrides.
  useEffect(() => {
    setOverrides(initialOverrides);
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const hasOverrides = Object.values(overrides).some((w) => Object.keys(w).length > 0);

  async function handleClearOverrides() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setOverrides({});
    await updateOverrides(sessionId, {});
    onOverrideChanged();
  }

  const rowData = useMemo<RowDataItem[]>(() => {
    if (!computeResponse) return [];
    return computeResponse.rows.map((row) => {
      const flat: RowDataItem = {
        label: row.label,
        budget_bucket: row.budget_bucket,
        priority: row.priority,
        estimation: row.estimation,
        total_weeks: row.total_weeks,
        off_estimate: row.off_estimate,
        _isEpic: isEpicRow(row),
        _isOffCapacity: row.label === 'Off Capacity',
      };
      for (const [week, val] of Object.entries(row.week_values)) {
        flat[week] = val;
      }
      return flat;
    });
  }, [computeResponse]);

  // Include `overrides` in deps so overridden cells get their amber highlight.
  const columnDefs = useMemo<ColDef[]>(() => {
    if (!computeResponse) return [];

    const fixedCols: ColDef[] = [
      { field: 'label', headerName: 'Label', pinned: 'left', width: 220, editable: false },
      { field: 'budget_bucket', headerName: 'Budget Bucket', width: 180, editable: false },
      { field: 'priority', headerName: 'Priority', width: 90, editable: false },
      { field: 'estimation', headerName: 'Estimation', width: 110, editable: false },
      { field: 'total_weeks', headerName: 'Total Weeks', width: 110, editable: false },
      {
        field: 'off_estimate',
        headerName: 'Off Estimate',
        width: 120,
        editable: false,
        cellStyle: (params) => (params.value === true ? OFF_STYLE : null),
      },
    ];

    const weekCols: ColDef[] = computeResponse.week_labels.map((week) => ({
      // Do NOT use `field` — AG Grid treats "." as a nested-path separator
      // (e.g. "Mar.30" → row.Mar.30). Use colId + valueGetter/valueSetter.
      colId: week,
      headerName: week,
      width: 90,
      valueGetter: (params) => params.data?.[week],
      valueSetter: (params) => { params.data[week] = params.newValue; return true; },
      editable: (params) => params.data?._isEpic === true,
      cellStyle: (params) => {
        if (params.data?._isOffCapacity && params.value === true) return OFF_STYLE;
        if (params.data?._isEpic) {
          const isOverridden = overrides[params.data.label]?.[week] !== undefined;
          return isOverridden ? OVERRIDDEN_STYLE : EDITABLE_STYLE;
        }
        return null;
      },
    }));

    return [...fixedCols, ...weekCols];
  }, [computeResponse, overrides]);

  const getRowStyle = useCallback((params: { data?: RowDataItem }) => {
    const bucket = params.data?.budget_bucket;
    if (bucket && BUDGET_BUCKET_COLORS[bucket]) {
      return { background: BUDGET_BUCKET_COLORS[bucket] };
    }
    return undefined;
  }, []);

  const handleCellValueChanged = useCallback(
    (event: CellValueChangedEvent) => {
      const row = event.data as RowDataItem;
      if (!row._isEpic) return;

      const epicLabel = row.label;
      // Use colId, not field — week columns use colId because field names contain "."
      const week = event.column.getColId();
      const value = Number(event.newValue);
      if (isNaN(value)) return;

      setOverrides((prev) => {
        const next = {
          ...prev,
          [epicLabel]: { ...(prev[epicLabel] ?? {}), [week]: value },
        };

        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(async () => {
          await updateOverrides(sessionId, next);
          onOverrideChanged();
        }, 300);

        return next;
      });
    },
    [sessionId, onOverrideChanged],
  );

  if (!computeResponse) {
    return <p className="text-gray-500 italic">No allocation computed yet.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {computeResponse.validation_errors.length > 0 && (
        <div className="rounded-md bg-red-50 border border-red-300 p-3 text-red-800 text-sm">
          <strong>Validation errors:</strong>
          <ul className="list-disc ml-5 mt-1">
            {computeResponse.validation_errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {computeResponse.has_overflow && (
        <div className="rounded-md bg-yellow-50 border border-yellow-300 p-3 text-yellow-800 text-sm">
          ⚠ Overflow: some epics extend into Q+1
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          Click any <span className="inline-block w-3 h-3 rounded-sm align-middle" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }} /> blue cell to override its allocation.
          Overridden cells are highlighted <span className="inline-block w-3 h-3 rounded-sm align-middle" style={{ background: '#FEF3C7', border: '1px solid #FDE68A' }} /> amber.
        </span>
        {hasOverrides && (
          <button
            type="button"
            onClick={handleClearOverrides}
            className="text-xs text-red-500 hover:text-red-700 hover:underline"
          >
            Clear all overrides
          </button>
        )}
      </div>

      <div className="ag-theme-alpine w-full">
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          domLayout="autoHeight"
          singleClickEdit={true}
          stopEditingWhenCellsLoseFocus={true}
          getRowStyle={getRowStyle}
          onCellValueChanged={handleCellValueChanged}
        />
      </div>
    </div>
  );
}

export { BUDGET_BUCKET_COLORS };

