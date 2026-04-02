import { describe, it, expect, vi } from 'vitest';

// Mock Vite env vars before importing supabaseClient
vi.stubEnv('VITE_SUPABASE_URL', 'https://mock.supabase.co');
vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'mock-anon-key');

import { supabase } from '../../lib/supabaseClient';

describe('supabaseClient', () => {
  it('should create a supabase client instance', () => {
    expect(supabase).toBeDefined();
    // In @supabase/supabase-js v2, auth is a property of the client
    expect(supabase.auth).toBeDefined();
  });
});
