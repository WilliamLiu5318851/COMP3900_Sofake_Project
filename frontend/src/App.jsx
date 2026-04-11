import React, { useMemo, useState } from "react";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import "./App.css";

function LogoMark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="SoFake logo">
      <path d="M10 18h44v28H10z" fill="currentColor" opacity="0.12" />
      <path d="M16 22h32v4H16zm0 8h28v4H16zm0 8h22v4H16z" fill="currentColor" />
      <path d="M46 46l8 8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
      <path d="M48 44a10 10 0 1 0-4 4" stroke="currentColor" strokeWidth="4" fill="none" />
    </svg>
  );
}

function Sidebar({ active, onNavigate }) {
  const items = [
    { id: "new", label: "New Simulation" },
    { id: "graph", label: "Graph View" },
    { id: "dashboard", label: "Overview Dashboard" },
    { id: "runs", label: "Saved Runs" },
    { id: "settings", label: "Settings" },
    { id: "about", label: "About" },
  ];
  return (
    <aside className="sidebar" aria-label="Sidebar navigation">
      <div className="sidebar__brand">
        <LogoMark size={24} />
        <div>
          <div className="sidebar__brandTitle">SoFake</div>
          <div className="sidebar__brandSubtitle">Truth drift simulator</div>
        </div>
      </div>
      <nav className="sidebar__nav">
        {items.map((it) => (
          <button
            key={it.id}
            className={`sidebar__item ${active === it.id ? "is-active" : ""}`}
            onClick={() => onNavigate(it.id)}
            type="button"
          >
            {it.label}
          </button>
        ))}
      </nav>
      <div className="sidebar__footer">
        <div className="pill">Offline • No scraping</div>
      </div>
    </aside>
  );
}

function Header({ title }) {
  return (
    <header className="header">
      <div className="header__left">
        <div>
          <h1 className="header__title">{title}</h1>
          <p className="header__subtitle">
            Submit ground truth → simulate agent interactions → measure Ground-Truth Change Score
          </p>
        </div>
      </div>
      <div className="header__right">
        <button className="btn btn--ghost" type="button">Import Dataset</button>
        <button className="btn" type="button">Export Report</button>
      </div>
    </header>
  );
}

function GroundTruthUploader({ value, onChange }) {
  const maxChars = 6000;
  const remaining = maxChars - value.length;
  return (
    <section className="card">
      <div className="card__header">
        <h2 className="card__title">Ground Truth Newsreel</h2>
        <div className={`card__meta ${remaining < 0 ? "is-bad" : ""}`}>
          {value.length.toLocaleString()} / {maxChars.toLocaleString()} chars
        </div>
      </div>
      <label className="label" htmlFor="groundTruth">
        Paste the original, truthful newsreel (text-only)
      </label>
      <textarea
        id="groundTruth"
        className="textarea"
        placeholder="Paste the ground truth here..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={10}
      />
      <div className="row row--between">
        <div className="hint">
          Tip: Keep it factual and complete (who/what/when/where). No URLs (out of scope).
        </div>
        <div className="row">
          <button className="btn btn--ghost" type="button" onClick={() => onChange("")}>Clear</button>
          <button
            className="btn btn--ghost"
            type="button"
            onClick={() =>
              onChange(`Scientists at a major US university have published a study suggesting that microplastics found in common bottled water brands may be interfering with human hormone regulation. The study, which tracked 3,000 participants over 5 years, found a statistically significant correlation between bottled water
            consumption and disrupted cortisol and thyroid levels. The lead researcher stated the findings are 'concerning but not yet conclusive'. Health authorities have not yet issued any official guidance in response to the study.`)
            }
          >
            Load Example
          </button>
        </div>
      </div>
    </section>
  );
}

function SimulationConfig({ config, setConfig }) {
  const roleSum = useMemo(
    () => Object.values(config.roleMix).reduce((a, b) => a + b, 0),
    [config.roleMix]
  );
  function setRole(role, val) {
    const n = Number(val);
    setConfig((c) => ({
      ...c,
      roleMix: { ...c.roleMix, [role]: Number.isFinite(n) ? n : 0 },
    }));
  }
  return (
    <section className="card">
      <div className="card__header">
        <h2 className="card__title">Simulation Settings</h2>
        <div className={`card__meta ${roleSum !== 100 ? "is-bad" : ""}`}>
          Role mix: {roleSum}% (target 100%)
        </div>
      </div>
      <div className="grid grid--2">
        <div>
          <label className="label">Number of agents</label>
          <input className="input" type="number" min={5} max={200} value={config.agentCount}
            onChange={(e) => setConfig((c) => ({ ...c, agentCount: Number(e.target.value) }))} />
        </div>
        <div>
          <label className="label">Topology</label>
          <select className="input" value={config.topology}
            onChange={(e) => setConfig((c) => ({ ...c, topology: e.target.value }))}>
            <option value="random">Random</option>
            <option value="clustered">High-clustering</option>
            <option value="scaleFree">Scale-free</option>
          </select>
        </div>
        <div>
          <label className="label">Seed (reproducibility)</label>
          <input className="input" type="number" value={config.seed}
            onChange={(e) => setConfig((c) => ({ ...c, seed: Number(e.target.value) }))} />
        </div>
        <div>
          <label className="label">Steps (interactions)</label>
          <input className="input" type="number" min={5} max={500} value={config.steps}
            onChange={(e) => setConfig((c) => ({ ...c, steps: Number(e.target.value) }))} />
        </div>
      </div>
      <div className="divider" />
      <h3 className="subhead">Role mix</h3>
      <div className="grid grid--4">
        {["spreader", "commentator", "verifier", "bystander"].map((role) => (
          <div key={role}>
            <label className="label">{role.charAt(0).toUpperCase() + role.slice(1)}s (%)</label>
            <input className="input" type="number" min={0} max={100} value={config.roleMix[role]}
              onChange={(e) => setRole(role, e.target.value)} />
          </div>
        ))}
      </div>
      {roleSum !== 100 && (
        <div className="callout callout--warn">Role mix should sum to 100% for clearer experiments.</div>
      )}
    </section>
  );
}

function RunActions({ canRun, loading, onRun }) {
  return (
    <section className="card">
      <h2 className="card__title">Run</h2>
      <div className="row">
        <button className="btn" type="button" disabled={!canRun || loading} onClick={onRun}>
          {loading ? "Running…" : "Start Simulation"}
        </button>
      </div>
      {!canRun && !loading && (
        <div className="callout callout--warn">
          Add ground truth text first (and keep it within the character limit).
        </div>
      )}
      {loading && (
        <div className="callout">
          Simulation in progress — this may take a minute depending on agent count and steps.
        </div>
      )}
    </section>
  );
}

// ── Shared data helpers ───────────────────────────────────────────────────────

function useRunData(run_log) {
  if (!run_log) return null;
  const allEvents = run_log.steps.flatMap((s) => s.events);
  const newPosts = allEvents.filter((e) => e.new_signals);

  const stepData = run_log.steps.map((s) => ({
    name: `Step ${s.step}`,
    posts: s.new_posts_this_step,
  }));

  const actionCounts = {};
  allEvents.forEach((e) => { actionCounts[e.action] = (actionCounts[e.action] || 0) + 1; });
  const actionData = Object.entries(actionCounts).map(([action, count]) => ({ action, count }));

  const genMap = {};
  const gt = run_log.ground_truth.signals;
  genMap[0] = { ec: [gt.emotional_charge], ct: [gt.controversy], fr: [gt.fringe_score], tl: [gt.threat_level] };
  newPosts.forEach((e) => {
    const g = e.new_signals.generation;
    if (!genMap[g]) genMap[g] = { ec: [], ct: [], fr: [], tl: [] };
    genMap[g].ec.push(e.new_signals.emotional_charge);
    genMap[g].ct.push(e.new_signals.controversy);
    genMap[g].fr.push(e.new_signals.fringe_score);
    genMap[g].tl.push(e.new_signals.threat_level);
  });
  const avg = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length;
  const driftData = Object.keys(genMap)
    .map(Number)
    .sort((a, b) => a - b)
    .map((g) => ({
      gen: `Gen ${g}`,
      "Emotional charge": +avg(genMap[g].ec).toFixed(2),
      Controversy: +avg(genMap[g].ct).toFixed(2),
      "Fringe score": +avg(genMap[g].fr).toFixed(2),
      "Threat level": +avg(genMap[g].tl).toFixed(2),
    }));

  const maxGen = Math.max(...newPosts.map((e) => e.new_signals.generation), 0);

  return { stepData, actionData, driftData, newPosts, maxGen, actionCounts };
}

function NoResultsYet() {
  return (
    <div className="callout">
      No simulation run yet — go to New Simulation to run one first.
    </div>
  );
}

// ── Graph View — signal drift line chart ─────────────────────────────────────

function GraphView({ simResult }) {
  const d = useRunData(simResult?.run_log);
  return (
    <section className="card">
      <h2 className="card__title">Graph View</h2>
      {!d ? <NoResultsYet /> : (
        <>
          <p className="hint" style={{ marginBottom: "1rem" }}>
            Signal drift across generations — how emotional charge, controversy, fringe score, and
            threat level evolve as the story propagates further from the ground truth.
          </p>
          <h3 className="subhead">Signal drift across generations</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={d.driftData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <XAxis dataKey="gen" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line dataKey="Emotional charge" stroke="#BA7517" dot strokeWidth={2} />
              <Line dataKey="Controversy" stroke="#7F77DD" dot strokeWidth={2} />
              <Line dataKey="Fringe score" stroke="#D85A30" dot strokeWidth={2} />
              <Line dataKey="Threat level" stroke="#E24B4A" dot strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </section>
  );
}

// ── FUSE Results ──────────────────────────────────────────────────────────────

const FUSE_DIMS = ["SS", "NII", "CS", "STS", "TS", "PD", "SI", "SAA", "PIB"];
const FUSE_LABELS = {
  SS: "Sentiment Shift", NII: "New Info", CS: "Certainty Shift",
  STS: "Stylistic Shift", TS: "Temporal Shift", PD: "Perspective Dev.",
  SI: "Sensationalism", SAA: "Source Alteration", PIB: "Political Bias",
};

function FuseResults({ fuseEvaluations }) {
  const [selected, setSelected] = useState(0);
  if (!fuseEvaluations || fuseEvaluations.length === 0) {
    return <div className="hint">No FUSE evaluations available.</div>;
  }
  const item = fuseEvaluations[selected];
  const scores = item.fuse_scores;
  const barData = FUSE_DIMS.map((k) => ({ dim: FUSE_LABELS[k], score: scores[k] ?? 0 }));
  return (
    <>
      <div className="row" style={{ marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.4rem" }}>
        {fuseEvaluations.map((e, i) => (
          <button
            key={e.post_id}
            className={`btn btn--ghost${i === selected ? " is-active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.2rem 0.6rem" }}
            onClick={() => setSelected(i)}
            type="button"
          >
            Step {e.step} · {e.author}
          </button>
        ))}
      </div>
      <div className="hint" style={{ marginBottom: "0.5rem" }}>
        <strong>{item.author}</strong> · {item.action} · Step {item.step}
        {" · "}Total Deviation: <strong>{scores.Total_Deviation}</strong>
        {" · "}Extended: <strong>{scores.Extended_Deviation}</strong>
      </div>
      <div className="hint" style={{ marginBottom: "0.75rem", fontStyle: "italic" }}>
        "{item.text}"
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={barData} margin={{ top: 4, right: 8, bottom: 40, left: 0 }}>
          <XAxis dataKey="dim" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
          <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="score" fill="#D85A30" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

// ── Overview Dashboard — metrics + bar charts ─────────────────────────────────

function OverviewDashboard({ simResult }) {
  const d = useRunData(simResult?.run_log);
  const run_log = simResult?.run_log;
  return (
    <>
      <section className="card">
        <h2 className="card__title">Overview Dashboard</h2>
        {!d ? <NoResultsYet /> : (
          <>
            {/* Summary metrics */}
            <div className="grid grid--2" style={{ marginBottom: "1rem" }}>
              <div><span className="label">Total posts generated</span><div>{d.newPosts.length}</div></div>
              <div><span className="label">Steps run</span><div>{run_log.steps.length}</div></div>
              <div><span className="label">Agents</span><div>{run_log.agents.length}</div></div>
              <div><span className="label">Max generation</span><div>{d.maxGen}</div></div>
            </div>

            <div className="divider" />

            {/* Posts per step */}
            <h3 className="subhead">Posts generated per step</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={d.stepData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="posts" fill="#1D9E75" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>

            <div className="divider" />

            {/* Actions breakdown */}
            <h3 className="subhead">Actions breakdown</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={d.actionData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <XAxis dataKey="action" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#7F77DD" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>

            <div className="divider" />

            {/* FUSE deviation scores */}
            <h3 className="subhead">FUSE Deviation Scores</h3>
            <FuseResults fuseEvaluations={simResult?.fuse_evaluations} />
          </>
        )}
      </section>
    </>
  );
}

// ── Saved Runs — full post timeline ──────────────────────────────────────────

function SavedRuns({ savedRuns }) {
  return (
    <section className="card">
      <h2 className="card__title">Saved Runs</h2>
      {savedRuns.length === 0 ? (
        <NoResultsYet />
      ) : (
        savedRuns.map((result, idx) => {
          const { run_log } = result;
          const textPosts = run_log.steps.flatMap((s) =>
            s.events.filter((e) => e.new_post_text)
          );
          return (
            <div key={run_log.run_id} style={{ marginBottom: idx < savedRuns.length - 1 ? "2rem" : 0 }}>
              <div className="card__header" style={{ marginBottom: "0.75rem" }}>
                <h3 className="subhead" style={{ margin: 0 }}>
                  Run {savedRuns.length - idx}: {run_log.run_id}
                </h3>
                <div className="hint">
                  {run_log.agents.length} agents · {run_log.steps.length} steps · seed {run_log.config.seed}
                </div>
              </div>

              <div className="grid grid--2" style={{ marginBottom: "0.75rem" }}>
                <div><span className="label">Posts generated</span><div>{textPosts.length}</div></div>
                <div>
                  <span className="label">Max generation</span>
                  <div>{Math.max(...run_log.steps.flatMap(s => s.events.filter(e => e.new_signals).map(e => e.new_signals.generation)), 0)}</div>
                </div>
              </div>

              <div style={{ maxHeight: "350px", overflowY: "auto" }}>
                {run_log.steps.flatMap((s) =>
                  s.events
                    .filter((e) => e.new_post_text)
                    .map((e) => (
                      <div
                        key={e.new_post_id}
                        style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--border)" }}
                      >
                        <div className="hint" style={{ marginBottom: "0.25rem" }}>
                          Step {s.step} · {e.agent_name} · {e.action} · Gen {e.new_signals.generation}
                          {" · "}EC {e.new_signals.emotional_charge.toFixed(2)}
                          {" · "}CT {e.new_signals.controversy.toFixed(2)}
                          {" · "}FR {e.new_signals.fringe_score.toFixed(2)}
                          {" · "}TL {e.new_signals.threat_level.toFixed(2)}
                        </div>
                        <div>{e.new_post_text}</div>
                      </div>
                    ))
                )}
              </div>

              {idx < savedRuns.length - 1 && <div className="divider" style={{ marginTop: "1.5rem" }} />}
            </div>
          );
        })
      )}
    </section>
  );
}

// ── Placeholder ───────────────────────────────────────────────────────────────

function PlaceholderPage({ title, children }) {
  return (
    <section className="card">
      <h2 className="card__title">{title}</h2>
      <div className="hint">{children}</div>
    </section>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState("new");
  const [groundTruth, setGroundTruth] = useState("");
  const [config, setConfig] = useState({
    agentCount: 30,
    topology: "random",
    seed: 42,
    steps: 60,
    roleMix: { spreader: 35, commentator: 35, verifier: 15, bystander: 15 },
  });
  const [loading, setLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [savedRuns, setSavedRuns] = useState([]);  // accumulates every completed run
  const [simError, setSimError] = useState(null);

  const withinLimit = groundTruth.length > 0 && groundTruth.length <= 6000;

  async function handleRun() {
    setLoading(true);
    setSimResult(null);
    setSimError(null);
    try {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ground_truth: groundTruth,
          agent_count: config.agentCount,
          steps: config.steps,
          seed: config.seed,
          role_mix: config.roleMix,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Simulation failed");
      }
      const data = await res.json();
      setSimResult(data);
      setSavedRuns((prev) => [data, ...prev]);  // newest first
    } catch (e) {
      setSimError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <Sidebar active={page} onNavigate={setPage} />
      <main className="main">
        <Header title="SoFake — Fake News Evolution Simulator" />
        <div className="content">

          {page === "new" && (
            <>
              <GroundTruthUploader value={groundTruth} onChange={setGroundTruth} />
              <SimulationConfig config={config} setConfig={setConfig} />
              <RunActions canRun={withinLimit} loading={loading} onRun={handleRun} />
              {simError && <div className="callout callout--warn">Error: {simError}</div>}
              {simResult && (
                <div className="callout">
                  Simulation complete — view results in Graph View, Overview Dashboard, and Saved Runs.
                </div>
              )}
            </>
          )}

          {page === "graph" && <GraphView simResult={simResult} />}

          {page === "dashboard" && <OverviewDashboard simResult={simResult} />}

          {page === "runs" && <SavedRuns savedRuns={savedRuns} />}

          {page === "settings" && (
            <PlaceholderPage title="Settings">
              Store defaults (max chars, step limit, role presets, scoring weights). Add "Reset to defaults".
            </PlaceholderPage>
          )}

          {page === "about" && (
            <PlaceholderPage title="About SoFake">
              Explain: no live detection, no scraping. It's a simulation tool to study how truth
              drifts through agent interactions.
            </PlaceholderPage>
          )}

        </div>
      </main>
    </div>
  );
}