import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BotDashboardPage from '../../pages/BotDashboardPage';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/bots', () => ({
  useBots: () => ({ data: [], isLoading: false, isError: false }),
  useUpdateBotState: () => ({ mutate: vi.fn() })
}));
vi.mock('../../stores/authStore', () => ({
  useAuthStore: () => ({ session: { access_token: 'valid' } })
}));

describe('BotDashboardPage', () => {
  it('renders Bot Dashboard text', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <BotDashboardPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Bot Dashboard/i)).toBeInTheDocument();
  });
});
