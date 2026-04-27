/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';
import { computeParallelFuseStats } from './fuseStats';

describe('SoFake Frontend Unit Tests', () => {

  // Test Case 1: Character count logic
  it('should calculate remaining characters correctly', () => {
    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste the ground truth here/i);

    fireEvent.change(textarea, { target: { value: 'Hello SoFake' } });

    expect(screen.getByText(/12 \/ 6,000 chars/i)).toBeDefined();
  });

  // Test Case 2: Role ratio sum validation
  it('should show warning when role mix does not sum to 100%', () => {
    render(<App />);

    expect(screen.queryByText(/Role mix should sum to 100%/i)).toBeNull();

    const allNumberInputs = screen.getAllByRole('spinbutton');
    // Layout: AgentCount(0), Seed(1), Steps(2), Spreaders(3)
    const spreaderInput = allNumberInputs[3];

    fireEvent.change(spreaderInput, { target: { value: '50' } });

    expect(screen.getByText(/Role mix should sum to 100%/i)).toBeDefined();
  });

  // Test Case 3: Start Simulation button state
  it('should disable Start Simulation button if ground truth is empty', () => {
    render(<App />);
    const runButton = screen.getByText(/Start Simulation/i);

    expect(runButton.closest('button')).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Paste the ground truth here/i);
    fireEvent.change(textarea, { target: { value: 'Valid Ground Truth' } });
    expect(runButton.closest('button')).not.toBeDisabled();
  });

  // Test Case 4: Page navigation
  it('should navigate to Graph View when sidebar item is clicked', () => {
    render(<App />);

    const graphLink = screen.getByText(/Graph View/i);
    fireEvent.click(graphLink);

    expect(screen.getByText(/Hook this to your run results/i)).toBeDefined();
  });
});

describe('computeParallelFuseStats', () => {
  const makeRun = (id, tdVal, dimVal) => ({
    run_log: { run_id: `20260417_000000_${id}` },
    fuse_evaluations: [
      {
        fuse_scores_vs_ground_truth: {
          SS: dimVal, NII: dimVal, CS: dimVal, STS: dimVal, TS: dimVal,
          PD: dimVal, SI: dimVal, SAA: dimVal, PIB: dimVal,
          Total_Deviation: tdVal,
        },
      },
    ],
  });

  it('computes per-run Total_Deviation averages', () => {
    const runs = [makeRun('run00', 6.0, 5.0), makeRun('run01', 8.0, 7.0)];
    const { runChart } = computeParallelFuseStats(runs);
    expect(runChart).toHaveLength(2);
    expect(runChart[0]).toEqual({ run: 'run00', td: 6.0 });
    expect(runChart[1]).toEqual({ run: 'run01', td: 8.0 });
  });

  it('computes global dimension averages and error bounds', () => {
    const runs = [makeRun('run00', 6.0, 4.0), makeRun('run01', 8.0, 8.0)];
    const { globalDims } = computeParallelFuseStats(runs);
    const ss = globalDims.find((d) => d.dim === 'SS');
    expect(ss.score).toBe(6.0);
    expect(ss.error).toEqual([2.0, 2.0]);
  });

  it('handles runs with empty fuse_evaluations', () => {
    const runs = [
      { run_log: { run_id: 'run00' }, fuse_evaluations: [] },
      makeRun('run01', 5.0, 5.0),
    ];
    const { runChart } = computeParallelFuseStats(runs);
    expect(runChart[0].td).toBe(0);
    expect(runChart[1].td).toBe(5.0);
  });
});
