import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UploadView } from './UploadView';

vi.mock('../api/client', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  uploadSession: vi.fn(),
}));

import * as client from '../api/client';

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('UploadView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (client.listSessions as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  it('renders file input and quarter selector', () => {
    renderWithProviders(<UploadView />);
    expect(screen.getByText(/drag & drop/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /quarter/i })).toBeInTheDocument();
  });

  it('shows error when upload attempted without file', async () => {
    renderWithProviders(<UploadView />);
    const uploadBtn = screen.getByRole('button', { name: /upload/i });
    await userEvent.click(uploadBtn);
    expect(await screen.findByRole('alert')).toHaveTextContent(/please select/i);
  });

  it('calls uploadSession with correct args on form submit', async () => {
    const mockSession = {
      session_id: 'abc123',
      filename: 'plan.xlsx',
      quarter: 2,
      capacity: { eng_bruto: 0, eng_absence: 0, mgmt_capacity: 0, mgmt_absence: 0, eng_bruto_by_week: {}, eng_absence_by_week: {} },
      epics: [],
      manual_overrides: {},
    };
    (client.uploadSession as ReturnType<typeof vi.fn>).mockResolvedValue(mockSession);

    renderWithProviders(<UploadView />);

    const file = new File(['dummy'], 'plan.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, file);

    const quarterSelect = screen.getByRole('combobox', { name: /quarter/i });
    await userEvent.selectOptions(quarterSelect, '2');

    const uploadBtn = screen.getByRole('button', { name: /upload/i });
    await userEvent.click(uploadBtn);

    await waitFor(() => {
      expect(client.uploadSession).toHaveBeenCalledWith(file, 2);
    });
  });
});
