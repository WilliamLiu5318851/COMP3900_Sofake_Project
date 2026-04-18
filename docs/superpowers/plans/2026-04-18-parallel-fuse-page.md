# Parallel FUSE Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Parallel FUSE" sidebar page that shows cross-run FUSE score comparisons when `simulations > 1`.

**Architecture:** All changes live in `frontend/src/App.jsx`. A new `ParallelFusePage` component reads `simResult.runs[]`, computes per-run and global averages via a pure helper function `computeParallelFuseStats`, and renders two recharts `BarChart`s. The Sidebar conditionally exposes the new nav entry only when `simResult?.runs?.length > 1`.

**Tech Stack:** React, recharts (`BarChart`, `Bar`, `ErrorBar`, `XAxis`, `YAxis`, `Tooltip`, `ResponsiveContainer`, `LabelList`), vitest + @testing-library/react

---

## File Map

| File | Action | What changes |
|---|---|---|
| `frontend/src/App.jsx` | Modify | Sidebar prop, new route, new component + helper |
| `frontend/src/App.test.jsx` | Modify | Tests for `computeParallelFuseStats` + sidebar visibility |

---

### Task 1: Extract and test `computeParallelFuseStats` helper

This pure function is the data backbone of `ParallelFusePage`. Extracting and testing it first means the rendering task has no hidden logic.

**Files:**
- Modify: `frontend/src/App.jsx` (add exported helper near top of file, after `FUSE_DIMS` constant)
- Modify: `frontend/src/App.test.jsx` (import and test the helper)

- [ ] **Step 1: Add `computeParallelFuseStats` to App.jsx**

Add this function immediately after the existing `FUSE_DIMS` and `FUSE_LABELS` constants (around line 357 in App.jsx):

```jsx
// Export for testing
export function computeParallelFuseStats(runs) {
  const DIMS = ["SS", "NII", "CS", "STS", "TS", "PD", "SI", "SAA", "PIB"];
  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

  // Per-run averages across all posts in that run
  const perRun = runs.map((run) => {
    const evals = run.fuse_evaluations || [];
    const dimAvgs = {};
    DIMS.forEach((dim) => {
      dimAvgs[dim] = avg(evals.map((e) => (e.fuse_scores_vs_ground_truth || {})[dim] ?? 0));
    });
    dimAvgs.Total_Deviation = avg(
      evals.map((e) => (e.fuse_scores_vs_ground_truth || {}).Total_Deviation ?? 0)
    );
    return { runId: run.run_log?.run_id ?? "unknown", ...dimAvgs };
  });

  // Global stats across all runs per dimension
  const globalDims = DIMS.map((dim) => {
    const vals = perRun.map((r) => r[dim]);
    const mean = avg(vals);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    return {
      dim,
      score: +mean.toFixed(2),
      error: [+(mean - min).toFixed(2), +(max - mean).toFixed(2)],
    };
  });

  // Per-run chart data
  const runChart = perRun.map((r) => ({
    run: r.runId.replace(/^\d{8}_\d{6}_/, ""),  // strip timestamp prefix for readability
    td: +r.Total_Deviation.toFixed(2),
  }));

  return { runChart, globalDims };
}
```

- [ ] **Step 2: Add import for the helper in App.test.jsx**

Add this import at the top of `frontend/src/App.test.jsx` (after existing imports):

```jsx
import { computeParallelFuseStats } from './App';
```

- [ ] **Step 3: Write failing tests for `computeParallelFuseStats`**

Add a new `describe` block at the end of `App.test.jsx`:

```jsx
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
    expect(ss.score).toBe(6.0);          // avg of 4.0 and 8.0
    expect(ss.error).toEqual([2.0, 2.0]); // [mean-min, max-mean]
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
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd frontend && npm test -- --run App.test.jsx
```

Expected: FAIL — `computeParallelFuseStats is not a function` (not exported yet)

- [ ] **Step 5: Verify tests pass after Step 1**

```bash
cd frontend && npm test -- --run App.test.jsx
```

Expected: all `computeParallelFuseStats` tests PASS. Existing 4 tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.test.jsx
git commit -m "feat: add computeParallelFuseStats helper with tests"
```

---

### Task 2: Add `ParallelFusePage` component

**Files:**
- Modify: `frontend/src/App.jsx` (add component after `FuseAgentReport`)

- [ ] **Step 1: Add `ParallelFusePage` component**

Add the following component to `App.jsx`, immediately before the `// ── App ───` comment block:

```jsx
// ── Parallel FUSE Page ────────────────────────────────────────────────────────

function ParallelFusePage({ simResult }) {
  const runs = simResult?.runs;

  if (!runs || runs.length < 2) {
    return (
      <div className="callout">
        Run at least 2 parallel simulations to see cross-run comparisons.
      </div>
    );
  }

  const { runChart, globalDims } = computeParallelFuseStats(runs);

  return (
    <>
      <section className="card">
        <h2 className="card__title">Total Deviation per Run</h2>
        <p className="hint" style={{ marginBottom: "1rem" }}>
          Average Total Deviation score across all evaluated posts, per simulation run.
        </p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={runChart} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
            <XAxis dataKey="run" tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="td" fill="#D85A30" radius={[4, 4, 0, 0]}>
              <LabelList dataKey="td" position="top" style={{ fontSize: 11 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section className="card">
        <h2 className="card__title">Average FUSE Dimensions (all runs)</h2>
        <p className="hint" style={{ marginBottom: "1rem" }}>
          Global average per dimension across all runs. Error bars show min–max range.
        </p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={globalDims} margin={{ top: 16, right: 16, bottom: 50, left: 0 }}>
            <XAxis dataKey="dim" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(val, name) => [val, name === "score" ? "Avg" : name]} />
            <Bar dataKey="score" fill="#7F77DD" radius={[4, 4, 0, 0]}>
              <ErrorBar dataKey="error" width={4} strokeWidth={2} stroke="#4a4a8a" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>
    </>
  );
}
```

- [ ] **Step 2: Add `LabelList` and `ErrorBar` to the recharts import at line 1**

Change the existing import:

```jsx
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
```

To:

```jsx
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  LabelList, ErrorBar,
} from "recharts";
```

- [ ] **Step 3: Run existing tests to confirm nothing is broken**

```bash
cd frontend && npm test -- --run App.test.jsx
```

Expected: all tests PASS (7 total — 4 original + 3 new)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add ParallelFusePage component"
```

---

### Task 3: Wire sidebar and routing

**Files:**
- Modify: `frontend/src/App.jsx` — `Sidebar` component + `App` render

- [ ] **Step 1: Update `Sidebar` to accept `simResult` prop and conditionally add entry**

Find the `Sidebar` function (around line 19) and change it from:

```jsx
function Sidebar({ active, onNavigate }) {
  const items = [
    { id: "new", label: "New Simulation" },
    { id: "graph", label: "Graph View" },
    { id: "dashboard", label: "Overview Dashboard" },
    { id: "fuse", label: "FUSE Comparison" },
    { id: "fuse-report", label: "FUSE Report" },
    { id: "runs", label: "Saved Runs" },
    { id: "settings", label: "Settings" },
    { id: "about", label: "About" },
  ];
```

To:

```jsx
function Sidebar({ active, onNavigate, simResult }) {
  const showParallel = (simResult?.runs?.length ?? 0) > 1;
  const items = [
    { id: "new", label: "New Simulation" },
    { id: "graph", label: "Graph View" },
    { id: "dashboard", label: "Overview Dashboard" },
    { id: "fuse", label: "FUSE Comparison" },
    { id: "fuse-report", label: "FUSE Report" },
    ...(showParallel ? [{ id: "parallel-fuse", label: "Parallel FUSE" }] : []),
    { id: "runs", label: "Saved Runs" },
    { id: "settings", label: "Settings" },
    { id: "about", label: "About" },
  ];
```

- [ ] **Step 2: Pass `simResult` to `Sidebar` in the `App` render**

Find the `<Sidebar` usage in the `App` return (around line 864):

```jsx
<Sidebar active={page} onNavigate={setPage} />
```

Change to:

```jsx
<Sidebar active={page} onNavigate={setPage} simResult={simResult} />
```

- [ ] **Step 3: Add `parallel-fuse` route in the `App` render**

Find the block of page routes (after `{page === "fuse-report" && ...}`):

```jsx
{page === "fuse-report" && <FuseAgentReport simResult={simResult} />}

{page === "runs" && <SavedRuns savedRuns={savedRuns} />}
```

Change to:

```jsx
{page === "fuse-report" && <FuseAgentReport simResult={simResult} />}

{page === "parallel-fuse" && <ParallelFusePage simResult={simResult} />}

{page === "runs" && <SavedRuns savedRuns={savedRuns} />}
```

- [ ] **Step 4: Run all tests**

```bash
cd frontend && npm test -- --run App.test.jsx
```

Expected: all 7 tests PASS. (The existing "Graph View" navigation test still passes because "Graph View" is still in the sidebar.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: wire Parallel FUSE sidebar entry and route"
```

---

## Self-Review

**Spec coverage:**
- [x] New sidebar page "Parallel FUSE" — Task 3
- [x] Only shown when `runs.length > 1` — Task 3, Step 1
- [x] Card 1: Total Deviation per Run BarChart — Task 2, Step 1
- [x] Card 2: Average FUSE Dimensions with ErrorBar — Task 2, Step 1
- [x] Data logic: per-run avg + global avg/min/max — Task 1

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:**
- `computeParallelFuseStats` returns `{ runChart, globalDims }` — used consistently in `ParallelFusePage`
- `runChart` items: `{ run: string, td: number }` — matches BarChart `dataKey`s
- `globalDims` items: `{ dim: string, score: number, error: [number, number] }` — matches BarChart + ErrorBar `dataKey`s
