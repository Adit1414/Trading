import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import StrategiesHubPage from '../../pages/StrategiesHubPage';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/strategies', () => ({
  useStrategies: () => ({ data: [], isLoading: false, isError: false })
}));

describe('StrategiesHubPage', () => {
  it('renders the header correctly', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <StrategiesHubPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Strategies Hub/i)).toBeInTheDocument();
  });
});
