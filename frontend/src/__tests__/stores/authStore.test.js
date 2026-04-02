import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '../../stores/authStore';

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, session: null, loading: true });
  });

  it('should initialize with default state', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.session).toBeNull();
    expect(state.loading).toBe(true);
  });

  it('should set user and session', () => {
    useAuthStore.getState().setUser({ id: '123' }, { access_token: 'abc' });
    const state = useAuthStore.getState();
    expect(state.user).toEqual({ id: '123' });
    expect(state.session).toEqual({ access_token: 'abc' });
    expect(state.loading).toBe(false);
  });

  it('should handle clearUser properly', () => {
    useAuthStore.getState().setUser({ id: '123' }, { access_token: 'abc' });
    useAuthStore.getState().clearUser();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.session).toBeNull();
    expect(state.loading).toBe(false);
  });
});
