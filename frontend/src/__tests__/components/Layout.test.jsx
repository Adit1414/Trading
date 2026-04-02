import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Layout from '../../components/Layout';
import { BrowserRouter } from 'react-router-dom';

vi.mock('../../stores/authStore', () => ({
  useAuthStore: () => ({ user: { id: 'test-user' }, clearUser: vi.fn() })
}));
vi.mock('../../lib/supabaseClient', () => ({
  supabase: { auth: { signOut: vi.fn() } }
}));

describe('Layout Component', () => {
  it('renders sidebar navigation links', () => {
    render(
      <BrowserRouter>
         <Layout />
      </BrowserRouter>
    );
    // Should render the application navigation links
    expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Backtest Engine/i)).toBeInTheDocument();
  });
});
