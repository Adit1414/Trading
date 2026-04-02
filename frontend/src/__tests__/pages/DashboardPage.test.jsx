import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DashboardPage from '../../pages/DashboardPage';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/backtests', () => ({
  useBacktests: () => ({ data: [], isLoading: false, isError: false })
}));
vi.mock('../../api/bots', () => ({
  useBots: () => ({ data: [], isLoading: false, isError: false })
}));

describe('DashboardPage', () => {
  it('renders Dashboard Overview text', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Dashboard Overview/i)).toBeInTheDocument();
  });
});
