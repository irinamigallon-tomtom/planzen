import { useCallback, useMemo, useRef, useState } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, ICellRendererParams, RowDragEndEvent } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community';
import { updateEpics } from '../api/client';
import type { Epic } from '../types';

ModuleRegistry.registerModules([AllCommunityModule]);

interface EpicsTableProps {
  sessionId: string;
  epics: Epic[];
  onEpicsChanged: () => void;
  debounceMs?: number;
}

const ALLOCATION_MODES = ['Sprint', 'Uniform', 'Gaps'];

export function EpicsTable({ sessionId, epics, onEpicsChanged, debounceMs = 500 }: EpicsTableProps) {
  const [rowData, setRowData] = useState<Epic[]>(() => [...epics].sort((a, b) => a.priority - b.priority));
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleUpdate = useCallback(
    (rows: Epic[]) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        await updateEpics(sessionId, rows);
        onEpicsChanged();
      }, debounceMs);
    },
    [sessionId, onEpicsChanged, debounceMs],
  );

  const duplicatePriorities = useMemo(() => {
    const counts = new Map<number, number>();
    for (const epic of rowData) {
      counts.set(epic.priority, (counts.get(epic.priority) ?? 0) + 1);
    }
    return [...counts.entries()]
      .filter(([, count]) => count > 1)
      .map(([p]) => p)
      .sort((a, b) => a - b);
  }, [rowData]);

  const handleCellValueChanged = useCallback(() => {
    setRowData((prev) => {
      scheduleUpdate(prev);
      return prev;
    });
  }, [scheduleUpdate]);

  const handleRowDragEnd = useCallback(
    (event: RowDragEndEvent) => {
      const api = event.api;
      const reordered: Epic[] = [];
      api.forEachNodeAfterFilterAndSort((node) => {
        if (node.data) reordered.push(node.data as Epic);
      });
      setRowData(reordered);
      scheduleUpdate(reordered);
    },
    [scheduleUpdate],
  );

  const DeleteRenderer = useCallback(
    (params: ICellRendererParams) => (
      <button
        className="text-red-500 hover:text-red-700 font-bold px-2"
        onClick={() => {
          const updated = rowData.filter((r) => r !== params.data);
          setRowData(updated);
          scheduleUpdate(updated);
        }}
      >
        ✕
      </button>
    ),
    [rowData, scheduleUpdate],
  );

  const columnDefs = useMemo<ColDef[]>(
    () => [
      { field: 'priority', headerName: 'Priority', editable: true, width: 90, rowDrag: true, sort: 'asc' },
      { field: 'epic_description', headerName: 'Epic', editable: true, flex: 2 },
      { field: 'estimation', headerName: 'Estimation (PW)', editable: true, width: 140, type: 'numericColumn' },
      { field: 'budget_bucket', headerName: 'Budget Bucket', editable: true, flex: 1 },
      {
        field: 'allocation_mode',
        headerName: 'Allocation Mode',
        editable: true,
        width: 150,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: { values: ALLOCATION_MODES },
      },
      { field: 'milestone', headerName: 'Milestone', editable: true, flex: 1 },
      { field: 'type', headerName: 'Type', editable: true, width: 100 },
      { field: 'link', headerName: 'Link', editable: true, flex: 1 },
      {
        headerName: '',
        width: 60,
        cellRenderer: DeleteRenderer,
        editable: false,
        sortable: false,
        filter: false,
        suppressMovable: true,
      },
    ],
    [DeleteRenderer],
  );

  const handleAddEpic = useCallback(() => {
    const newEpic: Epic = {
      epic_description: '',
      estimation: 1.0,
      budget_bucket: '',
      priority: 0,
      allocation_mode: 'Sprint',
      link: '',
      type: '',
      milestone: '',
    };
    const updated = [...rowData, newEpic];
    setRowData(updated);
    scheduleUpdate(updated);
  }, [rowData, scheduleUpdate]);

  return (
    <div className="flex flex-col gap-2">
      {duplicatePriorities.length > 0 && (
        <p
          className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2"
          role="status"
        >
          ℹ Duplicate priorities: {duplicatePriorities.join(', ')}. Epics with equal priority keep their original order.
        </p>
      )}
      <div className="flex justify-end">
        <button
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-1.5 rounded"
          onClick={handleAddEpic}
        >
          Add Epic
        </button>
      </div>
      <div className="ag-theme-alpine w-full">
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          domLayout="autoHeight"
          animateRows={true}
          rowDragManaged={true}
          onCellValueChanged={handleCellValueChanged}
          onRowDragEnd={handleRowDragEnd}
        />
      </div>
    </div>
  );
}
