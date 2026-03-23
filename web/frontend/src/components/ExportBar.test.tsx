import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportBar } from './ExportBar';

vi.mock('../api/client', () => ({
  exportSession: vi.fn(),
}));

import * as client from '../api/client';

global.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock');
global.URL.revokeObjectURL = vi.fn();

const defaultProps = { sessionId: 'sess-1', filename: 'myplan', quarter: 3 };

describe('ExportBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders button', () => {
    render(<ExportBar {...defaultProps} />);
    expect(screen.getByRole('button', { name: /download export/i })).toBeInTheDocument();
  });

  it('shows metadata', () => {
    render(<ExportBar {...defaultProps} />);
    expect(screen.getByText('myplan')).toBeInTheDocument();
    expect(screen.getByText(/Q3/)).toBeInTheDocument();
  });

  it('triggers download on click', async () => {
    const blob = new Blob(['data'], { type: 'application/zip' });
    vi.mocked(client.exportSession).mockResolvedValue(blob);

    const appendSpy = vi.spyOn(document.body, 'appendChild');

    render(<ExportBar {...defaultProps} />);
    await userEvent.click(screen.getByRole('button', { name: /download export/i }));

    expect(client.exportSession).toHaveBeenCalledWith('sess-1');
    expect(global.URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock');
    const anchor = appendSpy.mock.calls
      .map((c) => c[0] as HTMLElement)
      .find((el) => el.tagName === 'A');
    expect(anchor).toBeDefined();
    expect(anchor!.getAttribute('download')).toMatch(/^output_myplan_Q3_\d{12}_formulas\.xlsx$/);

    appendSpy.mockRestore();
  });

  it('shows error on failure', async () => {
    vi.mocked(client.exportSession).mockRejectedValue(new Error('Export failed'));

    render(<ExportBar {...defaultProps} />);
    await userEvent.click(screen.getByRole('button', { name: /download export/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Export failed');
  });

  it('button disabled during export', async () => {
    vi.mocked(client.exportSession).mockReturnValue(new Promise(() => {}));

    render(<ExportBar {...defaultProps} />);
    const button = screen.getByRole('button', { name: /download export/i });
    await userEvent.click(button);

    expect(screen.getByRole('button', { name: /exporting/i })).toBeDisabled();
  });
});
