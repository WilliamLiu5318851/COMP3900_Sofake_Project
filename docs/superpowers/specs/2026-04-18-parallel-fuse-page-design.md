# Parallel FUSE Page — Design Spec

**Date:** 2026-04-18  
**Scope:** Frontend only (`App.jsx`). FUSE section of the SoFake simulator.

---

## Context

When `simulations > 1`, the backend returns `simResult.runs` — an array where each element has `{ run_log, signal_drift, fuse_evaluations }`. Currently the frontend ignores everything except `runs[0]`. This spec adds a dedicated page to visualise cross-run FUSE comparisons.

---

## Goal

Show users two things when multiple parallel runs exist:
1. How Total Deviation differs across runs (which run produced the most drift)
2. What the average FUSE dimension scores look like across all runs combined

---

## Data Logic

Source: `simResult.runs[].fuse_evaluations`

Each run's representative score = average of `fuse_scores_vs_ground_truth` across all posts in that run.

```
per run:
  runAvg[dim] = mean(fuse_evaluations[*].fuse_scores_vs_ground_truth[dim])
  runTD       = mean(fuse_evaluations[*].fuse_scores_vs_ground_truth.Total_Deviation)

across all runs:
  globalAvg[dim] = mean(runAvg[dim] for all runs)
  globalMin[dim] = min(runAvg[dim] for all runs)
  globalMax[dim] = max(runAvg[dim] for all runs)
```

Computed in `useMemo` inside `ParallelFusePage`. No backend changes.

---

## Page Layout

**Entry condition:** Only shown in sidebar when `simResult?.runs?.length > 1`.

### Card 1 — Total Deviation per Run

- Title: `Total Deviation per Run`
- Chart: `BarChart` (recharts)
  - X axis: run ID (`run00`, `run01`, …)
  - Y axis: Total_Deviation mean for that run, domain [0, 10]
  - Label: value shown on each bar

### Card 2 — Average FUSE Dimensions (all runs)

- Title: `Average FUSE Dimensions (all runs)`
- Chart: `BarChart` (recharts)
  - X axis: 9 FUSE dimension abbreviations (SS, NII, CS, STS, TS, PD, SI, SAA, PIB)
  - Y axis: global average per dimension, domain [0, 10]
  - `ErrorBar`: shows min–max range across runs per dimension

---

## Integration Points (App.jsx only)

| Location | Change |
|---|---|
| `Sidebar` component | Accept `simResult` prop; conditionally include `{ id: "parallel-fuse", label: "Parallel FUSE" }` in items |
| `App` render | Add `{page === "parallel-fuse" && <ParallelFusePage simResult={simResult} />}` |
| New component | `ParallelFusePage` — self-contained, no changes to existing components |

---

## Out of Scope

- Run selector on existing FUSE pages (Graph View, FUSE Comparison, FUSE Report)
- Backend changes
- Saving/exporting parallel results
