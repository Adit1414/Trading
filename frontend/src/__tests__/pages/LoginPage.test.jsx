import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LoginPage from '../../pages/LoginPage';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../stores/authStore', () => ({
  useAuthStore: () => ({
    signIn: vi.fn(),
    signUp: vi.fn(),
    signInGuest: vi.fn(),
    isAuthenticated: false,
    loading: false
  })
}));

describe('LoginPage', () => {
  it('renders sign in header', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByRole('heading', { name: /Sign in to your account/i })).toBeInTheDocument();
  });
});
