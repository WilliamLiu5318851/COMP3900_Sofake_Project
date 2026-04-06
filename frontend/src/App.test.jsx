/**
 * @vitest-environment jsdom
 */
import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';

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
