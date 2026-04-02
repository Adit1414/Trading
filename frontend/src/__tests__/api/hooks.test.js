import { describe, it, expect, vi } from 'vitest';

// We mock the react query hooks existence since testing React components inside Vitest needs testing-library
describe('API Hooks existence', () => {
  it('should export backtest hooks', async () => {
    const hooks = await import('../../api/backtests');
    expect(hooks.useBacktests).toBeDefined();
    expect(hooks.useBacktestDetails).toBeDefined();
    expect(hooks.useRunBacktest).toBeDefined();
  });

  it('should export bot hooks', async () => {
    const hooks = await import('../../api/bots');
    expect(hooks.useBots).toBeDefined();
    expect(hooks.useCreateBot).toBeDefined();
    expect(hooks.useUpdateBotState).toBeDefined();
  });

  it('should export strategy hooks', async () => {
    const hooks = await import('../../api/strategies');
    expect(hooks.useStrategies).toBeDefined();
  });
});
