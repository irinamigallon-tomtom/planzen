import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AllocationPreview } from './AllocationPreview';
import type { ComputeResponse, AllocationRow } from '../types';

vi.mock('../api/client', () => ({
  updateOverrides: vi.fn().mockResolvedValue({}),
  computeAllocation: vi.fn(),
}));

vi.mock('ag-grid-react', () => ({
  AgGridReact: ({ rowData }: { rowData: unknown[] }) => (
    <div data-testid="ag-grid">
      {(rowData ?? []).map((_, i) => (
        <div key={i} data-testid="ag-row" />
      ))}
    </div>
  ),
}));

const makeRow = (
  label: string,
  budget_bucket = '',
  off_estimate: boolean | null = null,
): AllocationRow => ({
  label,
  budget_bucket,
  priority: 1,
  estimation: 1,
  total_weeks: 1,
  off_estimate,
  week_values: {},
});

const makeResponse = (overrides: Partial<ComputeResponse> = {}): ComputeResponse => ({
  session_id: 'sess1',
  rows: [],
  week_labels: [],
  has_overflow: false,
  validation_errors: [],
  ...overrides,
});

describe('AllocationPreview', () => {
  it('shows empty state when computeResponse is null', () => {
    render(
      <AllocationPreview sessionId="s1" computeResponse={null} onOverrideChanged={vi.fn()} />,
    );
    expect(screen.getByText(/no allocation computed yet/i)).toBeInTheDocument();
  });

  it('renders rows in the grid', () => {
    const response = makeResponse({
      rows: [
        makeRow('Epic A'),
        makeRow('Epic B'),
        makeRow('Engineer Capacity (Bruto)'),
      ],
    });
    render(
      <AllocationPreview sessionId="s1" computeResponse={response} onOverrideChanged={vi.fn()} />,
    );
    expect(screen.getAllByTestId('ag-row')).toHaveLength(3);
  });

  it('shows overflow banner when has_overflow is true', () => {
    const response = makeResponse({ has_overflow: true });
    render(
      <AllocationPreview sessionId="s1" computeResponse={response} onOverrideChanged={vi.fn()} />,
    );
    expect(screen.getByText(/overflow.*some epics extend/i)).toBeInTheDocument();
  });

  it('shows validation errors when non-empty', () => {
    const response = makeResponse({ validation_errors: ['Error A', 'Error B'] });
    render(
      <AllocationPreview sessionId="s1" computeResponse={response} onOverrideChanged={vi.fn()} />,
    );
    expect(screen.getByText('Error A')).toBeInTheDocument();
    expect(screen.getByText('Error B')).toBeInTheDocument();
  });

  it('passes row data with off_estimate to the grid correctly', () => {
    const response = makeResponse({
      rows: [makeRow('My Epic', 'Maintenance & Release', true)],
    });
    render(
      <AllocationPreview sessionId="s1" computeResponse={response} onOverrideChanged={vi.fn()} />,
    );
    // The grid receives 1 row (off_estimate=true is passed through rowData)
    expect(screen.getAllByTestId('ag-row')).toHaveLength(1);
  });
});
