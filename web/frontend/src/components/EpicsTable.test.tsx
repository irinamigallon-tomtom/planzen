import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EpicsTable } from './EpicsTable';
import type { Epic } from '../types';

vi.mock('../api/client', () => ({
  updateEpics: vi.fn().mockResolvedValue({ session_id: 'test', epics: [] }),
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

import * as client from '../api/client';

const makeEpics = (count: number): Epic[] =>
  Array.from({ length: count }, (_, i) => ({
    epic_description: `Epic ${i + 1}`,
    estimation: 1.0,
    budget_bucket: `Bucket ${i + 1}`,
    priority: i + 1,
    allocation_mode: 'Sprint' as const,
    link: '',
    type: '',
    milestone: '',
  }));

describe('EpicsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all epics', () => {
    const epics = makeEpics(3);
    render(
      <EpicsTable sessionId="sess1" epics={epics} onEpicsChanged={vi.fn()} />,
    );
    expect(screen.getAllByTestId('ag-row')).toHaveLength(3);
  });

  it('add epic button exists', () => {
    render(
      <EpicsTable sessionId="sess1" epics={makeEpics(1)} onEpicsChanged={vi.fn()} />,
    );
    expect(screen.getByRole('button', { name: /add epic/i })).toBeInTheDocument();
  });

  it('calls updateEpics on add after debounce', async () => {
    render(
      <EpicsTable sessionId="sess1" epics={makeEpics(2)} onEpicsChanged={vi.fn()} debounceMs={0} />,
    );

    const addBtn = screen.getByRole('button', { name: /add epic/i });
    await userEvent.click(addBtn);

    await waitFor(() => {
      expect(client.updateEpics).toHaveBeenCalledWith(
        'sess1',
        expect.arrayContaining([expect.objectContaining({ priority: 0, allocation_mode: 'Sprint' })]),
      );
    });
  });

  it('shows duplicate priority warning when priorities are not unique', () => {
    const epics: Epic[] = [
      { epic_description: 'A', estimation: 1, budget_bucket: '', priority: 2, allocation_mode: 'Sprint', link: '', type: '', milestone: '' },
      { epic_description: 'B', estimation: 1, budget_bucket: '', priority: 2, allocation_mode: 'Sprint', link: '', type: '', milestone: '' },
      { epic_description: 'C', estimation: 1, budget_bucket: '', priority: 3, allocation_mode: 'Sprint', link: '', type: '', milestone: '' },
    ];
    render(<EpicsTable sessionId="sess1" epics={epics} onEpicsChanged={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveTextContent('Duplicate priorities: 2');
  });

  it('does not show duplicate priority warning when priorities are unique', () => {
    render(<EpicsTable sessionId="sess1" epics={makeEpics(3)} onEpicsChanged={vi.fn()} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('calls onEpicsChanged after successful update', async () => {
    const onEpicsChanged = vi.fn();
    render(
      <EpicsTable sessionId="sess1" epics={makeEpics(1)} onEpicsChanged={onEpicsChanged} debounceMs={0} />,
    );

    const addBtn = screen.getByRole('button', { name: /add epic/i });
    await userEvent.click(addBtn);

    await waitFor(() => {
      expect(onEpicsChanged).toHaveBeenCalled();
    });
  });
});
