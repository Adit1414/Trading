import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MetricCard from '../../components/MetricCard';

describe('MetricCard Component', () => {
  it('renders title and value', () => {
    render(<MetricCard title="Test Metric" value="123" />);
    expect(screen.getByText(/Test Metric/i)).toBeInTheDocument();
    expect(screen.getByText(/123/i)).toBeInTheDocument();
  });
});
