import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BacktestDetailPage from '../../pages/BacktestDetailPage';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/backtests', () => ({
  useBacktestDetails: () => ({ data: { id: 'test-123', symbol: 'BTCUSDT', metrics: {} }, isLoading: false, isError: false })
}));

describe('BacktestDetailPage', () => {
  it('renders correctly', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <BacktestDetailPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Backtest Details/i)).toBeInTheDocument();
  });
});
