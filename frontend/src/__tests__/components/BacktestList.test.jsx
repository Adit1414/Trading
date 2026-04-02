import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BacktestList from '../../components/BacktestList';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/backtests', () => ({
  useBacktests: () => ({ data: [], isLoading: false, isError: false }),
  useDeleteBacktest: () => ({ mutate: vi.fn(), isPending: false })
}));

describe('BacktestList Component', () => {
  it('renders an empty list message if no data', () => {
    render(
      <QueryClientProvider client={queryClient}>
         <BacktestList onSelect={vi.fn()} onDeleteClick={vi.fn()} />
      </QueryClientProvider>
    );
    expect(screen.getByText(/No backtests found/i)).toBeInTheDocument();
  });
});
