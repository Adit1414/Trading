import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BacktestPage from '../../pages/BacktestPage';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/backtests', () => ({
  useBacktests: () => ({ data: [], isLoading: false, isError: false }),
  useDeleteBacktest: () => ({ mutate: vi.fn(), isPending: false }),
  useRunBacktest: () => ({ mutateAsync: vi.fn(), isPending: false })
}));
vi.mock('../../api/strategies', () => ({
  useStrategies: () => ({ data: [] })
}));

describe('BacktestPage', () => {
  it('renders header text', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <BacktestPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Backtest Engine/i)).toBeInTheDocument();
  });
});
