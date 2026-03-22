import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { CapacityEditor } from './CapacityEditor';

vi.mock('../api/client', () => ({
  updateCapacity: vi.fn().mockResolvedValue({}),
}));

import * as client from '../api/client';

const baseCapacity = {
  eng_bruto: 5.0,
  eng_absence: 0.7,
  mgmt_capacity: 2.0,
  mgmt_absence: 0.3,
  eng_bruto_by_week: {},
  eng_absence_by_week: {},
};

describe('CapacityEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders all four scalar fields with correct initial values', () => {
    render(
      <CapacityEditor
        sessionId="s1"
        capacity={baseCapacity}
        onCapacityChanged={vi.fn()}
      />,
    );

    expect(screen.getByRole('spinbutton', { name: /eng_bruto/i })).toHaveValue(5);
    expect(screen.getByRole('spinbutton', { name: /eng_absence/i })).toHaveValue(0.7);
    expect(screen.getByRole('spinbutton', { name: /mgmt_capacity/i })).toHaveValue(2);
    expect(screen.getByRole('spinbutton', { name: /mgmt_absence/i })).toHaveValue(0.3);
  });

  it('calls updateCapacity after debounce when eng_bruto changes', async () => {
    const onCapacityChanged = vi.fn();

    render(
      <CapacityEditor
        sessionId="s1"
        capacity={baseCapacity}
        onCapacityChanged={onCapacityChanged}
      />,
    );

    const input = screen.getByRole('spinbutton', { name: /eng_bruto/i });
    fireEvent.change(input, { target: { value: '8' } });

    // Before debounce fires — should not have been called yet
    expect(client.updateCapacity).not.toHaveBeenCalled();

    // Advance past 500ms debounce and flush microtasks
    await act(async () => {
      vi.advanceTimersByTime(600);
      await Promise.resolve();
    });

    expect(client.updateCapacity).toHaveBeenCalledWith(
      's1',
      expect.objectContaining({ eng_bruto: 8 }),
    );
  });

  it('calls onCapacityChanged after a successful API call', async () => {
    const onCapacityChanged = vi.fn();

    render(
      <CapacityEditor
        sessionId="s1"
        capacity={baseCapacity}
        onCapacityChanged={onCapacityChanged}
      />,
    );

    const input = screen.getByRole('spinbutton', { name: /eng_bruto/i });
    fireEvent.change(input, { target: { value: '6' } });

    await act(async () => {
      vi.advanceTimersByTime(600);
      await Promise.resolve();
    });

    expect(onCapacityChanged).toHaveBeenCalled();
  });
});
