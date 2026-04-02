import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CreateBotPage from '../../pages/CreateBotPage';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

vi.mock('../../api/bots', () => ({
  useCreateBot: () => ({ mutateAsync: vi.fn(), isPending: false })
}));
vi.mock('../../api/strategies', () => ({
  useStrategies: () => ({ data: [] })
}));

describe('CreateBotPage', () => {
  it('renders Create a New Trading Bot text', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CreateBotPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Create a New Trading Bot/i)).toBeInTheDocument();
  });
});
