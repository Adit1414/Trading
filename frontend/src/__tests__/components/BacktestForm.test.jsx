import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BacktestForm from '../../components/BacktestForm';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

// Mock dependencies
vi.mock('../../api/strategies', () => ({
  useStrategies: () => ({ data: [], isLoading: false })
}));
vi.mock('../../api/backtests', () => ({
  useRunBacktest: () => ({ mutateAsync: vi.fn(), isPending: false })
}));

describe('BacktestForm Component', () => {
  it('renders base form elements', () => {
    render(
      <QueryClientProvider client={queryClient}>
         <BacktestForm />
      </QueryClientProvider>
    );
    // Looking for the "Run Backtest" button
    expect(screen.getByText(/Run Backtest/i)).toBeInTheDocument();
  });
});
