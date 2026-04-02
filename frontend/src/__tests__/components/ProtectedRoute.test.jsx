import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProtectedRoute from '../../components/ProtectedRoute';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

// Mock zustand to simulate authenticated/unauthenticated state
vi.mock('../../stores/authStore', () => ({
  useAuthStore: vi.fn()
}));

const TestComponent = () => <div>Protected Content</div>;

describe('ProtectedRoute Component', () => {
  it('redirects to login when unauthenticated', () => {
    useAuthStore.mockImplementation(() => false); // Returns false for isAuthenticated
    
    render(
      <MemoryRouter initialEntries={['/protected']}>
         <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route path="/protected" element={<ProtectedRoute><TestComponent /></ProtectedRoute>} />
         </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Login Page/i)).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    useAuthStore.mockImplementation(() => true); // Returns true for isAuthenticated
    
    render(
      <MemoryRouter initialEntries={['/protected']}>
         <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route path="/protected" element={<ProtectedRoute><TestComponent /></ProtectedRoute>} />
         </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
  });
});
