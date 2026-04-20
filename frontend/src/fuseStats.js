const FUSE_DIMS = ["SS", "NII", "CS", "STS", "TS", "PD", "SI", "SAA", "PIB"];

export function computeParallelFuseStats(runs) {
  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

  const perRun = runs.map((run) => {
    const evals = run.fuse_evaluations || [];
    const dimAvgs = {};
    FUSE_DIMS.forEach((dim) => {
      dimAvgs[dim] = avg(evals.map((e) => (e.fuse_scores_vs_ground_truth || {})[dim] ?? 0));
    });
    dimAvgs.Total_Deviation = avg(
      evals.map((e) => (e.fuse_scores_vs_ground_truth || {}).Total_Deviation ?? 0)
    );
    return { runId: run.run_log?.run_id ?? "unknown", ...dimAvgs };
  });

  const globalDims = FUSE_DIMS.map((dim) => {
    const vals = perRun.map((r) => r[dim]);
    if (vals.length === 0) return { dim, score: 0, error: [0, 0] };
    const mean = avg(vals);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    return {
      dim,
      score: +mean.toFixed(2),
      error: [+(mean - min).toFixed(2), +(max - mean).toFixed(2)],
    };
  });

  const runChart = perRun.map((r) => ({
    run: r.runId.replace(/^\d{8}_\d{6}_/, ""),
    td: +r.Total_Deviation.toFixed(2),
  }));

  return { runChart, globalDims };
}
