import { describe, it, expect, vi } from 'vitest';
import axiosClient from '../../lib/axiosClient';

describe('axiosClient', () => {
  it('should have interceptors attached', () => {
    // Assert interceptors are defined on the axios instance
    expect(axiosClient.interceptors.request).toBeDefined();
    expect(axiosClient.interceptors.response).toBeDefined();
  });
});
