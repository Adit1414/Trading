import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PortfolioPerformanceCard from '../../components/PortfolioPerformanceCard';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

// Mock Recharts to avoid dom rendering issues
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  LineChart: ({ children }) => <div>{children}</div>,
  Line: () => <div>Line</div>,
  XAxis: () => <div>XAxis</div>,
  YAxis: () => <div>YAxis</div>,
  CartesianGrid: () => <div>CartesianGrid</div>,
  Tooltip: () => <div>Tooltip</div>
}));

describe('PortfolioPerformanceCard Component', () => {
  it('renders successfully', () => {
    render(
      <QueryClientProvider client={queryClient}>
         <PortfolioPerformanceCard />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Portfolio Performance/i)).toBeInTheDocument();
  });
});
