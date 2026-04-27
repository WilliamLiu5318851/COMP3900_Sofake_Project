import { useEffect, useState, useRef } from "react";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  LabelList, ErrorBar,
} from "recharts";
import "./App.css";
import { computeParallelFuseStats } from "./fuseStats";

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

function Header({ title, selectedRun }) {
  function handleExport() {
    if (!selectedRun) return;
    const blob = new Blob([JSON.stringify(selectedRun, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `run_log_${selectedRun?.run_log?.run_id ?? "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

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
        <button className="btn" type="button" disabled={!selectedRun} onClick={handleExport}>
          Export Report
        </button>
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
        Paste the original newsreel (text-only)
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
          Tip: Keep it factual and complete (who/what/when/where). No URLs.
        </div>
        <div className="row">
          <button className="btn btn--ghost" type="button" onClick={() => onChange("")}>Clear</button>
          <button
            className="btn btn--ghost"
            type="button"
            onClick={() =>
              onChange(`Scientists at a major US university have published a study suggesting that microplastics found in common bottled water brands may be interfering with human hormone regulation. The study, which tracked 3,000 participants over 5 years, found a statistically significant correlation between bottled water consumption and disrupted cortisol and thyroid levels. The lead researcher stated the findings are 'concerning but not yet conclusive'. Health authorities have not yet issued any official guidance in response to the study.`)
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
  return (
    <section className="card">
      <div className="card__header">
        <h2 className="card__title">Simulation Settings</h2>
      </div>

      {/* Core run settings */}
      <div className="grid grid--2">
        <div>
          <label className="label">Number of agents</label>
          <input
            className="input"
            type="number"
            min={5}
            max={200}
            value={config.agentCount || ""}
            onChange={(e) => setConfig((c) => ({ ...c, agentCount: Number(e.target.value) }))}
            style={config.agentCount === "" || config.agentCount === 0 ? { border: "1px solid red" } : {}}
          />
        </div>
        <div>
          <label className="label">Steps (interactions)</label>
          <input
            className="input"
            type="number"
            min={1}
            max={500}
            value={config.steps || ""}
            onChange={(e) => setConfig((c) => ({ ...c, steps: Number(e.target.value) }))}
            style={config.steps === "" || config.steps === 0 ? { border: "1px solid red" } : {}}
          />
        </div>
        <div>
          <label className="label">Seed (reproducibility)</label>
          <input
            className="input"
            type="number"
            value={config.seed || ""}
            onChange={(e) => setConfig((c) => ({ ...c, seed: Number(e.target.value) }))}
            style={config.seed === "" || config.seed === null ? { border: "1px solid red" } : {}}
          />
        </div>
        <div>
          <label className="label">Simulations (Run in parallel)</label>
          <input
            className="input"
            type="number"
            min={1}
            max={30}
            value={config.simulations || ""}
            onChange={(e) => setConfig((c) => ({ ...c, simulations: Number(e.target.value) }))}
            style={config.simulations === "" || config.simulations === 0 ? { border: "1px solid red" } : {}}
          />
        </div>
      </div>

      <div className="divider" />

      {/* Network topology */}
      <h3 className="subhead">Network Topology</h3>
      <div className="grid grid--2">
        <div>
          <label className="label">intra-cluster probability</label>
          <input
            className="input"
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={config.intraClusterP || ""}
            onChange={(e) => setConfig((c) => ({ ...c, intraClusterP: Number(e.target.value) }))}
            style={config.intraClusterP === "" || config.intraClusterP === 0 ? { border: "1px solid red" } : {}}
          />
          <div className="hint" style={{ marginTop: 4 }}>
            Erdős–Rényi edge probability within each cluster (0–1). Higher = denser clusters.
          </div>
        </div>
        <div>
          <label className="label">hub-to-hub edges (m)</label>
          <input
            className="input"
            type="number"
            min={1}
            max={10}
            step={1}
            value={config.interClusterM || ""}
            onChange={(e) => setConfig((c) => ({ ...c, interClusterM: Number(e.target.value) }))}
            style={config.interClusterM === "" || config.interClusterM === 0 ? { border: "1px solid red" } : {}}
          />
          <div className="hint" style={{ marginTop: 4 }}>
            Edges each hub forms to existing hubs (Barabási–Albert style). Controls cross-cluster connectivity.
          </div>
        </div>
        <div>
          <label className="label">Agents per cluster</label>
          <input
            className="input"
            type="number"
            min={2}
            max={50}
            step={1}
            value={config.agentsPerCluster || ""}
            onChange={(e) => setConfig((c) => ({ ...c, agentsPerCluster: Number(e.target.value) }))}
            style={config.agentsPerCluster === "" || config.agentsPerCluster === 0 ? { border: "1px solid red" } : {}}

          />
          <div className="hint" style={{ marginTop: 4 }}>
            Target cluster size — determines the number of clusters (≈ agents ÷ this value).
          </div>
        </div>
        <div>
          <label className="label">Weak tie probability</label>
          <input
            className="input"
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={config.weakTieP || ""}
            onChange={(e) => setConfig((c) => ({ ...c, weakTieP: Number(e.target.value) }))}
            style={config.weakTieP === "" || config.weakTieP === 0 ? { border: "1px solid red" } : {}}
          />
          <div className="hint" style={{ marginTop: 4 }}>
            Probability of forming weak ties between agents in different clusters (0–1).
          </div>
        </div>
      </div>
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

// ── Network Graph (pan + zoom + draggable nodes + hover tooltips) ─────────────
// Drop this in as a full replacement for the NetworkGraph component in App.jsx.
// Everything above and below it in App.jsx stays unchanged.

const CLUSTER_COLORS = [
  "#1D9E75", "#7F77DD", "#D85A30", "#BA7517",
  "#E24B4A", "#3A7BD5", "#F5A623", "#7ED321",
];

const HEXACO_LABELS = {
  honesty_humility:  "Honesty / Humility",
  emotionality:      "Emotionality",
  extraversion:      "Extraversion",
  agreeableness:     "Agreeableness",
  conscientiousness: "Conscientiousness",
  openness:          "Openness",
};

function HexacoBar({ value }) {
  const pct   = Math.round(value * 100);
  const color = value >= 0.66 ? "#1D9E75" : value >= 0.33 ? "#BA7517" : "#D85A30";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: "rgba(255,255,255,0.15)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.2s",
          }}
        />
      </div>
      <span style={{ fontSize: 10, opacity: 0.8, minWidth: 28, textAlign: "right" }}>
        {pct}%
      </span>
    </div>
  );
}

function AgentTooltip({ agent, screenX, screenY, containerRef }) {
  const ttRef = useRef(null);
  const [pos, setPos] = useState({ left: screenX + 14, top: screenY - 10 });

  // Nudge tooltip back on screen if it overflows the container
  useEffect(() => {
    if (!ttRef.current || !containerRef.current) return;
    const tt  = ttRef.current.getBoundingClientRect();
    const ct  = containerRef.current.getBoundingClientRect();
    let left  = screenX + 14;
    let top   = screenY - 10;
    if (left + tt.width  > ct.width)  left = screenX - tt.width - 14;
    if (top  + tt.height > ct.height) top  = screenY - tt.height;
    if (top < 0) top = 4;
    setPos({ left, top }); // eslint-disable-line react-hooks/set-state-in-effect
  }, [screenX, screenY, containerRef]);

  const p = agent.profile;

  return (
    <div
      ref={ttRef}
      style={{
        position:      "absolute",
        left:          pos.left,
        top:           pos.top,
        zIndex:        100,
        pointerEvents: "none",
        background:    "rgba(20,20,28,0.93)",
        color:         "#f0f0f0",
        borderRadius:  10,
        padding:       "0.75rem 1rem",
        minWidth:      220,
        boxShadow:     "0 8px 32px rgba(0,0,0,0.4)",
        backdropFilter: "blur(4px)",
        border:        "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.6rem" }}>
        <div
          style={{
            width: 10, height: 10, borderRadius: "50%",
            background: CLUSTER_COLORS[agent._clusterIdx % CLUSTER_COLORS.length],
            flexShrink: 0,
          }}
        />
        <span style={{ fontWeight: 700, fontSize: 13 }}>{agent.name}</span>
        {agent.is_hub && (
          <span
            style={{
              fontSize: 9, fontWeight: 700,
              background: "rgba(255,255,255,0.15)",
              padding: "1px 6px", borderRadius: 4,
              letterSpacing: "0.05em", textTransform: "uppercase",
            }}
          >
            Hub
          </span>
        )}
      </div>

      <div style={{ fontSize: 10, opacity: 0.5, marginBottom: "0.6rem" }}>
        Cluster {agent._clusterIdx + 1} · Agent #{agent.id}
      </div>

      {/* HEXACO bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        {Object.entries(HEXACO_LABELS).map(([key, label]) => (
          <div key={key}>
            <div style={{ fontSize: 10, opacity: 0.65, marginBottom: 2 }}>{label}</div>
            <HexacoBar value={p[key] ?? 0} />
          </div>
        ))}
      </div>
    </div>
  );
}

function NetworkGraph({ runLog }) {
  const W = 720, H = 520;

  const [positions, setPositions]       = useState(null);
  const [transform, setTransform]       = useState({ x: 0, y: 0, k: 1 });
  const [hoveredAgent, setHoveredAgent] = useState(null); // { agent, screenX, screenY }

  const posRef       = useRef({});
  const velRef       = useRef({});
  const frameRef     = useRef(null);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const svgRef       = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => { transformRef.current = transform; }, [transform]);

  // ── Force simulation ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!runLog?.agents?.length) return;

    const agents = runLog.agents;
    const edges  = runLog.network_edges || [];

    const pos = {}, vel = {};
    agents.forEach((a, i) => {
      const angle = (i / agents.length) * 2 * Math.PI;
      pos[a.id] = { x: W / 2 + 180 * Math.cos(angle), y: H / 2 + 160 * Math.sin(angle) };
      vel[a.id] = { x: 0, y: 0 };
    });
    posRef.current = pos;
    velRef.current = vel;

    let alpha = 1;

    const tick = () => {
      alpha *= 0.97;
      const p   = posRef.current;
      const v   = velRef.current;
      const ids = agents.map((a) => a.id);
      const fx  = Object.fromEntries(ids.map((id) => [id, 0]));
      const fy  = Object.fromEntries(ids.map((id) => [id, 0]));

      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const a = ids[i], b = ids[j];
          const dx = p[b].x - p[a].x, dy = p[b].y - p[a].y;
          const d  = Math.sqrt(dx * dx + dy * dy) || 1;
          const f  = 3500 / (d * d);
          fx[a] -= (f * dx) / d; fy[a] -= (f * dy) / d;
          fx[b] += (f * dx) / d; fy[b] += (f * dy) / d;
        }
      }

      edges.forEach(({ source, target }) => {
        if (!p[source] || !p[target]) return;
        const dx = p[target].x - p[source].x, dy = p[target].y - p[source].y;
        const d  = Math.sqrt(dx * dx + dy * dy) || 1;
        const f  = (d - 90) * 0.055;
        fx[source] += (f * dx) / d; fy[source] += (f * dy) / d;
        fx[target] -= (f * dx) / d; fy[target] -= (f * dy) / d;
      });

      ids.forEach((id) => {
        fx[id] += (W / 2 - p[id].x) * 0.018;
        fy[id] += (H / 2 - p[id].y) * 0.018;
      });

      ids.forEach((id) => {
        v[id].x = (v[id].x + fx[id] * alpha) * 0.78;
        v[id].y = (v[id].y + fy[id] * alpha) * 0.78;
        p[id] = {
          x: Math.max(20, Math.min(W - 20, p[id].x + v[id].x)),
          y: Math.max(20, Math.min(H - 20, p[id].y + v[id].y)),
        };
      });

      setPositions({ ...p });
      if (alpha > 0.004) frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [runLog]);

  function clientToContainer(cx, cy) {
    const rect = containerRef.current.getBoundingClientRect();
    return { x: cx - rect.left, y: cy - rect.top };
  }

  // ── Hover ─────────────────────────────────────────────────────────────────
  function handleNodeMouseEnter(e, agent) {
    const { x, y } = clientToContainer(e.clientX, e.clientY);
    setHoveredAgent({ agent, screenX: x, screenY: y });
  }

  function handleNodeMouseMove(e) {
    if (!hoveredAgent) return;
    const { x, y } = clientToContainer(e.clientX, e.clientY);
    setHoveredAgent((prev) => prev ? { ...prev, screenX: x, screenY: y } : prev);
  }

  function handleNodeMouseLeave() {
    setHoveredAgent(null);
  }

  function zoomIn() {
    const t    = transformRef.current;
    const newK = Math.min(8, t.k * 1.25);
    const next = {
      x: W / 2 - (W / 2 - t.x) * (newK / t.k),
      y: H / 2 - (H / 2 - t.y) * (newK / t.k),
      k: newK,
    };
    transformRef.current = next;
    setTransform(next);
  }
  
  function zoomOut() {
    const t    = transformRef.current;
    const newK = Math.max(0.2, t.k * 0.8);
    const next = {
      x: W / 2 - (W / 2 - t.x) * (newK / t.k),
      y: H / 2 - (H / 2 - t.y) * (newK / t.k),
      k: newK,
    };
    transformRef.current = next;
    setTransform(next);
  }

  // ── Reset view ────────────────────────────────────────────────────────────
  function resetView() {
    const next = { x: 0, y: 0, k: 1 };
    transformRef.current = next;
    setTransform(next);
  }

  function arrowhead(x1, y1, x2, y2, size = 7) {
    const dx = x2 - x1, dy = y2 - y1;
    const d  = Math.sqrt(dx * dx + dy * dy) || 1;
    const ux = dx / d, uy = dy / d;   // unit vector toward target
    const px = -uy,    py = ux;        // perpendicular
  
    // tip sits exactly at (x2, y2), base is `size` units back
    const tip  = { x: x2,                          y: y2 };
    const bl   = { x: x2 - ux * size + px * (size * 0.4), y: y2 - uy * size + py * (size * 0.4) };
    const br   = { x: x2 - ux * size - px * (size * 0.4), y: y2 - uy * size - py * (size * 0.4) };
  
    return `${tip.x},${tip.y} ${bl.x},${bl.y} ${br.x},${br.y}`;
  }

  // ── Render ────────────────────────────────────────────────────────────────
  if (!runLog) return <div className="hint">No simulation run yet.</div>;

  const agents   = runLog.agents;
  const edges    = runLog.network_edges || [];
  const agentMap = Object.fromEntries(agents.map((a) => [a.id, a]));

  const clusterIds = [...new Set(agents.map((a) => a.cluster))];
  const clusterColor = Object.fromEntries(
    clusterIds.map((cid, i) => [cid, CLUSTER_COLORS[i % CLUSTER_COLORS.length]])
  );

  // Attach _clusterIdx to each agent so the tooltip colour dot matches
  const agentsWithIdx = agents.map((a) => ({
    ...a,
    _clusterIdx: clusterIds.indexOf(a.cluster),
  }));

  const step         = edges.length > 400 ? Math.ceil(edges.length / 400) : 1;
  const displayEdges = edges.filter((_, i) => i % step === 0);

  if (!positions) {
    return (
      <div className="hint" style={{ padding: "2rem", textAlign: "center" }}>
        Building layout…
      </div>
    );
  }

  const { x: tx, y: ty, k: tk } = transform;

  return (
    <div>
      {/* Controls bar */}
      <div className="row" style={{ marginBottom: "0.5rem", gap: "0.5rem", alignItems: "center" }}>
        <span className="hint">
          Hover nodes for profile
        </span>
        <div className="row" style={{ marginLeft: "auto", gap: "0.25rem", alignItems: "center" }}>
          <button
            className="btn btn--ghost"
            style={{ fontSize: "1.1rem", padding: "0.15rem 0.6rem", lineHeight: 1 }}
            onClick={zoomOut}
            type="button"
            title="Zoom out"
          >
            −
          </button>
          <span className="hint" style={{ minWidth: 38, textAlign: "center" }}>
            {Math.round(tk * 100)}%
          </span>
          <button
            className="btn btn--ghost"
            style={{ fontSize: "1.1rem", padding: "0.15rem 0.6rem", lineHeight: 1 }}
            onClick={zoomIn}
            type="button"
            title="Zoom in"
          >
            +
          </button>
          <button
            className="btn btn--ghost"
            style={{ fontSize: "0.8rem", padding: "0.25rem 0.75rem" }}
            onClick={resetView}
            type="button"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Canvas wrapper — position:relative anchors the tooltip */}
      <div
        ref={containerRef}
        style={{
          position:    "relative",
          width:       "100%",
          overflow:    "hidden",
          borderRadius: 8,
          background:  "var(--surface-2, #f5f5f5)",
          userSelect:  "none",
          touchAction: "none",
        }}
      >
        <svg
          ref={svgRef}
          width="100%"
          viewBox={`0 0 ${W} ${H}`}
          style={{ display: "block" }}
          onMouseMove={handleNodeMouseMove}
        >
          <defs>
          <marker id="ngarrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
            <path d="M0,0 L5,2.5 L0,5 z" fill="#aaa" />
          </marker>
          </defs>

          <g transform={`translate(${tx},${ty}) scale(${tk})`}>

            {/* Edges */}
            {displayEdges.map((e, i) => {
              const sp = positions[e.source], tp = positions[e.target];
              if (!sp || !tp) return null;
              const dx = tp.x - sp.x, dy = tp.y - sp.y;
              const d  = Math.sqrt(dx * dx + dy * dy) || 1;

              // Stop the line exactly at the node boundary
              const targetR = agentMap[e.target]?.is_hub ? 14 : 8;
              const sourceR = agentMap[e.source]?.is_hub ? 14 : 8;
              const arrowSize = 7;

              // Line ends where the arrowhead base starts (targetR + arrowSize back from centre)
              const x2 = tp.x - (dx / d) * (targetR + arrowSize);
              const y2 = tp.y - (dy / d) * (targetR + arrowSize);
              const x1 = sp.x + (dx / d) * sourceR;
              const y1 = sp.y + (dy / d) * sourceR;

              // Arrowhead tip sits exactly on the node boundary
              const tipX = tp.x - (dx / d) * targetR;
              const tipY = tp.y - (dy / d) * targetR;

              return (
                <g key={i}>
                  <line
                    x1={x1} y1={y1}
                    x2={x2} y2={y2}
                    stroke="#c0c0c0"
                    strokeWidth={0.9}
                    opacity={0.8}
                  />
                  <polygon
                    points={arrowhead(x1, y1, tipX, tipY, arrowSize)}
                    fill="#b0b0b0"
                    opacity={0.9}
                  />
                </g>
              );
            })}

            {/* Nodes */}
            {agentsWithIdx.map((a) => {
              const p         = positions[a.id];
              if (!p) return null;
              const color     = clusterColor[a.cluster] || "#999";
              const isHovered = hoveredAgent?.agent?.id === a.id;

              return (
                <g
                  key={a.id}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={(e) => handleNodeMouseEnter(e, a)}
                  onMouseLeave={handleNodeMouseLeave}
                >
                  {a.is_hub ? (
                    <polygon
                      points={`${p.x},${p.y - 13} ${p.x + 11.3},${p.y + 6.5} ${p.x - 11.3},${p.y + 6.5}`}
                      fill={color}
                      stroke="white"
                      strokeWidth={isHovered ? 3 : 2}
                      style={{ filter: isHovered ? "brightness(1.25)" : "none" }}
                    />
                  ) : (
                    <circle
                      cx={p.x} cy={p.y}
                      r={isHovered ? 9 : 7}
                      fill={color}
                      stroke="white"
                      strokeWidth={isHovered ? 2.5 : 1.5}
                      style={{ filter: isHovered ? "brightness(1.25)" : "none" }}
                    />
                  )}
                  {a.is_hub && (
                    <text
                      x={p.x} y={p.y - 17}
                      textAnchor="middle"
                      fontSize={10}
                      fontWeight="700"
                      fill="var(--text, #222)"
                      style={{ pointerEvents: "none" }}
                    >
                      {a.name}
                    </text>
                  )}
                </g>
              );
            })}

          </g>
        </svg>

        {/* Tooltip rendered as an HTML overlay inside the container */}
        {hoveredAgent && (
          <AgentTooltip
            agent={hoveredAgent.agent}
            screenX={hoveredAgent.screenX}
            screenY={hoveredAgent.screenY}
            containerRef={containerRef}
          />
        )}
      </div>

      {/* Legend */}
      <div
        className="row"
        style={{ marginTop: "0.75rem", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}
      >
        {clusterIds.map((cid, i) => {
          const hubName = runLog.network?.hubs?.[String(cid)];
          return (
            <div key={cid} className="row" style={{ gap: "0.35rem", alignItems: "center" }}>
              <div style={{ width: 12, height: 12, borderRadius: "50%", background: clusterColor[cid] }} />
              <span className="hint">Cluster {i + 1}{hubName ? ` · ${hubName}` : ""}</span>
            </div>
          );
        })}
        <div className="row" style={{ gap: "0.35rem", alignItems: "center" }}>
          <svg width={14} height={14} viewBox="0 0 14 14">
            <polygon points="7,0 14,14 0,14" fill="#666" />
          </svg>
          <span className="hint">Hub node</span>
        </div>
        <div className="row" style={{ gap: "0.35rem", alignItems: "center" }}>
          <svg width={14} height={14}><circle cx={7} cy={7} r={5} fill="#666" /></svg>
          <span className="hint">Regular agent</span>
        </div>
      </div>

      <div className="hint" style={{ marginTop: "0.5rem" }}>
        {agents.length} agents · {edges.length} directed edges
        {edges.length > 400 ? ` (showing ${displayEdges.length} for clarity)` : ""}
      </div>
    </div>
  );
}

function GraphView({ simResult }) {
  const d = useRunData(simResult?.run_log);
  return (
    <>
      {/* Agent network topology */}
      <section className="card">
        <h2 className="card__title">Agent Network</h2>
        {!simResult?.run_log ? (
          <NoResultsYet />
        ) : (
          <>
            <p className="hint" style={{ marginBottom: "1rem" }}>
              Force-directed layout of the simulated social graph.{" "}
              <strong>Triangles</strong> are hub agents (highest extraversion);{" "}
              <strong>circles</strong> are regular agents. Colour indicates cluster.
              Arrows show directed follow relationships.
            </p>
            <NetworkGraph runLog={simResult.run_log} />
          </>
        )}
      </section>

      {/* Signal drift line chart */}
      <section className="card">
        <h2 className="card__title">Signal Drift Across Generations</h2>
        {!d ? (
          <NoResultsYet />
        ) : (
          <>
            <p className="hint" style={{ marginBottom: "1rem" }}>
              How emotional charge, controversy, fringe score, and threat level evolve
              as the story propagates further from the ground truth.
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={d.driftData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <XAxis dataKey="gen" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line dataKey="Emotional charge" stroke="#BA7517" dot strokeWidth={2} />
                <Line dataKey="Controversy"      stroke="#7F77DD" dot strokeWidth={2} />
                <Line dataKey="Fringe score"     stroke="#D85A30" dot strokeWidth={2} />
                <Line dataKey="Threat level"     stroke="#E24B4A" dot strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </section>
    </>
  );
}

// ── FUSE Results ──────────────────────────────────────────────────────────────

const FUSE_DIMS = ["SS", "NII", "CS", "STS", "TS", "PD", "SI", "SAA", "PIB"];
const FUSE_LABELS = {
  SS: "Sentiment Shift", NII: "New Info", CS: "Certainty Shift",
  STS: "Stylistic Shift", TS: "Temporal Shift", PD: "Perspective Dev.",
  SI: "Sensationalism", SAA: "Source Alteration", PIB: "Political Bias",
};

// Export for testing

const HEXACO_KEYS = Object.keys(HEXACO_LABELS);

function HexacoProfileChart({ profile }) {
  if (!profile) return null;
  const data = HEXACO_KEYS.map((k) => ({
    trait: HEXACO_LABELS[k],
    value: +((profile[k] ?? 0) * 10).toFixed(1),
  }));
  return (
    <div style={{ marginTop: "0.75rem" }}>
      <div className="hint" style={{ marginBottom: "0.4rem", fontWeight: 600 }}>HEXACO Personality Profile</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 50, left: 0 }}>
          <XAxis dataKey="trait" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
          <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(val) => [`${val}/10`, "Score"]} />
          <Bar dataKey="value" fill="#4A90D9" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FuseAgentReport({ simResult }) {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const evals = simResult?.fuse_evaluations;

  if (!simResult) return <div className="callout">No simulation run yet — go to New Simulation first.</div>;
  if (!evals || evals.length === 0) return <div className="callout">No FUSE evaluations in this run.</div>;

  // Build agent name → HEXACO profile map from run_log
  const agentProfileMap = {};
  (simResult.run_log?.agents ?? []).forEach((a) => {
    agentProfileMap[a.name] = a.profile;
  });

  // Group evaluations by agent
  const agentMap = {};
  evals.forEach((ev) => {
    if (!agentMap[ev.author]) agentMap[ev.author] = [];
    agentMap[ev.author].push(ev);
  });
  const agentNames = Object.keys(agentMap);

  // Default to first agent
  const activeAgent = selectedAgent && agentMap[selectedAgent] ? selectedAgent : agentNames[0];
  const agentPosts = agentMap[activeAgent] || [];
  const activeProfile = agentProfileMap[activeAgent] ?? null;

  // Calculate per-agent average across all posts
  const agentAvg = {};
  FUSE_DIMS.forEach((dim) => {
    const vals = agentPosts.map((p) => (p.fuse_scores_vs_ground_truth || {})[dim] ?? 0);
    agentAvg[dim] = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  });
  const avgTotalDeviation = agentPosts.length > 0
    ? agentPosts.reduce((sum, p) => sum + ((p.fuse_scores_vs_ground_truth || {}).Total_Deviation ?? 0), 0) / agentPosts.length
    : 0;
  const avgExtendedDeviation = agentPosts.length > 0
    ? agentPosts.reduce((sum, p) => sum + ((p.fuse_scores_vs_ground_truth || {}).Extended_Deviation ?? 0), 0) / agentPosts.length
    : 0;

  // Bar data for agent average
  const avgBarData = FUSE_DIMS.map((k) => ({
    dim: FUSE_LABELS[k],
    score: +agentAvg[k].toFixed(2),
  }));

  return (
    <section className="card">
      <h2 className="card__title">FUSE Agent Report</h2>
      <p className="hint" style={{ marginBottom: "1rem" }}>
        Per-agent breakdown of FUSE scores. Select an agent to view their posts' deviation scores
        and overall average.
      </p>

      {/* Agent tabs */}
      <div className="row" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.4rem" }}>
        {agentNames.map((name) => (
          <button
            key={name}
            className={`btn btn--ghost${name === activeAgent ? " is-active" : ""}`}
            style={{ fontSize: "0.8rem", padding: "0.3rem 0.8rem" }}
            onClick={() => setSelectedAgent(name)}
            type="button"
          >
            {name} ({agentMap[name].length})
          </button>
        ))}
      </div>

      {/* Agent average summary */}
      <div style={{
        background: "var(--surface-2, #f5f5f5)",
        borderRadius: "8px",
        padding: "1rem",
        marginBottom: "1rem",
        borderLeft: "4px solid #1D9E75",
      }}>
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
          <div>
            <div className="hint">Agent</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{activeAgent}</div>
          </div>
          <div>
            <div className="hint">Posts Evaluated</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{agentPosts.length}</div>
          </div>
          <div>
            <div className="hint">Avg Total Deviation</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#D85A30" }}>
              {avgTotalDeviation.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="hint">Avg Extended Deviation</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#7F77DD" }}>
              {avgExtendedDeviation.toFixed(2)}
            </div>
          </div>
        </div>

        {activeProfile && <HexacoProfileChart profile={activeProfile} />}

        <h3 className="subhead" style={{ marginTop: "1rem" }}>Average FUSE Dimensions</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={avgBarData} margin={{ top: 4, right: 8, bottom: 40, left: 0 }}>
            <XAxis dataKey="dim" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="score" fill="#1D9E75" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Per-post breakdown */}
      <h3 className="subhead">Post-by-Post Scores</h3>
      {agentPosts
        .sort((a, b) => a.step - b.step)
        .map((post, idx) => {
          const scores = post.fuse_scores_vs_ground_truth || {};
          const postBarData = FUSE_DIMS.map((k) => ({
            dim: FUSE_LABELS[k],
            score: scores[k] ?? 0,
          }));
          return (
            <div
              key={post.post_id}
              style={{
                marginBottom: "1rem",
                padding: "0.75rem",
                background: "var(--surface-2, #f5f5f5)",
                borderRadius: "6px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <div>
                  <span className="label">P{idx + 1}</span>
                  <span className="hint" style={{ marginLeft: "0.5rem" }}>
                    Step {post.step} · {post.action} · TD: <strong>{scores.Total_Deviation ?? "—"}</strong> · Ext: <strong>{scores.Extended_Deviation ?? "—"}</strong>
                  </span>
                </div>
              </div>
              <div className="hint" style={{ marginBottom: "0.5rem", fontStyle: "italic" }}>
                "{post.text}"
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={postBarData} margin={{ top: 4, right: 8, bottom: 40, left: 0 }}>
                  <XAxis dataKey="dim" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="score" fill="#D85A30" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          );
        })}
    </section>
  );
}

function FuseResults({ fuseEvaluations }) {
  const [selected, setSelected] = useState(0);
  if (!fuseEvaluations || fuseEvaluations.length === 0) {
    return <div className="hint">No FUSE evaluations available.</div>;
  }
  const item = fuseEvaluations[selected];
  const scores = item.fuse_scores_vs_ground_truth || item.fuse_scores || {};
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

// ── FUSE Comparison Page ──────────────────────────────────────────────────────

function ScoreBadge({ label, td, extended, color }) {
  return (
    <div style={{
      background: "var(--surface-2, #f5f5f5)",
      borderRadius: "8px",
      padding: "0.6rem 1rem",
      minWidth: "140px",
      borderLeft: `4px solid ${color}`,
    }}>
      <div className="hint" style={{ marginBottom: "0.2rem" }}>{label}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: 700, color }}>{td ?? "—"}</div>
      <div className="hint">TD · Extended: {extended ?? "—"}</div>
    </div>
  );
}

function FuseComparisonPage({ simResult }) {
  const [selected, setSelected] = useState(0);
  const evals = simResult?.fuse_evaluations;

  if (!simResult) return <div className="callout">No simulation run yet — go to New Simulation first.</div>;
  if (!evals || evals.length === 0) return <div className="callout">No FUSE evaluations in this run.</div>;

  const item = evals[selected];
  const gtScores = item.fuse_scores_vs_ground_truth || {};
  const parentScores = item.fuse_scores_vs_parent || null;

  const gtBarData = FUSE_DIMS.map((k) => ({
    dim: FUSE_LABELS[k],
    "vs Ground Truth": gtScores[k] ?? 0,
    ...(parentScores ? { "vs Parent Post": parentScores[k] ?? 0 } : {}),
  }));

  return (
    <section className="card">
      <h2 className="card__title">FUSE Comparison</h2>
      <p className="hint" style={{ marginBottom: "1rem" }}>
        Each evolved post is scored twice: once against the original ground truth, and once against
        the parent post it was responding to (if applicable).
      </p>

      {/* Post selector */}
      <div className="row" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.4rem" }}>
        {evals.map((e, i) => (
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

      {/* Score summary badges */}
      <div className="row" style={{ gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <ScoreBadge
          label="vs Ground Truth"
          td={gtScores.Total_Deviation}
          extended={gtScores.Extended_Deviation}
          color="#D85A30"
        />
        {parentScores ? (
          <ScoreBadge
            label="vs Parent Post"
            td={parentScores.Total_Deviation}
            extended={parentScores.Extended_Deviation}
            color="#7F77DD"
          />
        ) : (
          <div style={{ padding: "0.6rem 1rem" }} className="hint">
            Parent post = ground truth (no separate parent score)
          </div>
        )}
      </div>

      {/* Post texts */}
      <div className="grid grid--2" style={{ marginBottom: "1rem", gap: "1rem" }}>
        <div>
          <div className="label" style={{ marginBottom: "0.25rem" }}>Evolved post ({item.author} · {item.action})</div>
          <div style={{
            background: "var(--surface-2, #f5f5f5)",
            borderRadius: "6px",
            padding: "0.75rem",
            fontSize: "0.875rem",
            fontStyle: "italic",
          }}>
            "{item.text}"
          </div>
        </div>
        {item.parent_text && item.source_post_id !== "ground_truth" && (
          <div>
            <div className="label" style={{ marginBottom: "0.25rem" }}>Parent post</div>
            <div style={{
              background: "var(--surface-2, #f5f5f5)",
              borderRadius: "6px",
              padding: "0.75rem",
              fontSize: "0.875rem",
              fontStyle: "italic",
            }}>
              "{item.parent_text}"
            </div>
          </div>
        )}
      </div>

      {/* Grouped bar chart */}
      <h3 className="subhead">Dimension-by-dimension breakdown</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={gtBarData} margin={{ top: 4, right: 8, bottom: 50, left: 0 }}>
          <XAxis dataKey="dim" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} />
          <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend verticalAlign="top" />
          <Bar dataKey="vs Ground Truth" fill="#D85A30" radius={[3, 3, 0, 0]} />
          {parentScores && <Bar dataKey="vs Parent Post" fill="#7F77DD" radius={[3, 3, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    </section>
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
            <div className="grid grid--2" style={{ marginBottom: "1rem" }}>
              <div><span className="label">Total posts generated</span><div>{d.newPosts.length}</div></div>
              <div><span className="label">Steps run</span><div>{run_log.steps.length}</div></div>
              <div><span className="label">Agents</span><div>{run_log.agents.length}</div></div>
              <div><span className="label">Max generation</span><div>{d.maxGen}</div></div>
            </div>

            <div className="divider" />

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

// ── Saved Runs ────────────────────────────────────────────────────────────────

function getAllTextPosts(run_log) {
  return run_log.steps.flatMap((s) =>
    s.events
      .filter((e) => e.new_post_text)
      .map((e) => ({
        id: e.new_post_id,
        step: s.step,
        author: e.agent_name,
        action: e.action,
        text: e.new_post_text,
        generation: e.new_signals?.generation ?? 0,
        emotional: e.new_signals?.emotional_charge ?? 0,
        controversy: e.new_signals?.controversy ?? 0,
        fringe: e.new_signals?.fringe_score ?? 0,
        threat: e.new_signals?.threat_level ?? 0,
      }))
  );
}

function getMaxGenerationFromRun(run_log) {
  return Math.max(
    0,
    ...run_log.steps.flatMap((s) =>
      s.events
        .filter((e) => e.new_signals)
        .map((e) => e.new_signals.generation ?? 0)
    )
  );
}

function getAllFuseEvaluations(result) {
  if (result?.runs?.length) {
    return result.runs.flatMap((run) => run.fuse_evaluations || []);
  }
  return result?.fuse_evaluations || [];
}

function getAvgTotalDeviation(result) {
  const evals = getAllFuseEvaluations(result);
  if (!evals.length) return null;

  const total = evals.reduce(
    (sum, item) =>
      sum + ((item.fuse_scores_vs_ground_truth || {}).Total_Deviation ?? 0),
    0
  );

  return +(total / evals.length).toFixed(2);
}

function getTopDriftDimension(result) {
  const evals = getAllFuseEvaluations(result);
  if (!evals.length) return "N/A";

  const averages = FUSE_DIMS.map((dim) => {
    const total = evals.reduce(
      (sum, item) =>
        sum + ((item.fuse_scores_vs_ground_truth || {})[dim] ?? 0),
      0
    );
    return {
      dim,
      score: total / evals.length,
    };
  });

  const top = averages.sort((a, b) => b.score - a.score)[0];
  return FUSE_LABELS[top.dim];
}

function formatRunTimestamp(runId) {
  const match = runId?.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
  if (!match) return runId;

  const [, year, month, day, hour, minute, second] = match;
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

function SavedRuns({ savedRuns, selectedRun, onSelectRun, onDeleteRun }) {
  const [expandedRunId, setExpandedRunId] = useState(null);
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState("newest");

  const clamp2 = {
    display: "-webkit-box",
    WebkitLineClamp: 2,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
  };

  const visibleRuns = [...savedRuns]
    .filter((result) => {
      const q = query.trim().toLowerCase();
      if (!q) return true;

      const runId = result.run_log?.run_id?.toLowerCase() || "";
      const gt = (result.ground_truth_content || "").toLowerCase();
      return runId.includes(q) || gt.includes(q);
    })
    .sort((a, b) => {
      if (sortBy === "highest-drift") {
        return (getAvgTotalDeviation(b) ?? -1) - (getAvgTotalDeviation(a) ?? -1);
      }

      if (sortBy === "most-posts") {
        return getAllTextPosts(b.run_log).length - getAllTextPosts(a.run_log).length;
      }

      // newest first
      return (b.run_log?.run_id || "").localeCompare(a.run_log?.run_id || "");
    });

  return (
    <section className="card">
      <div className="card__header">
        <div>
          <h2 className="card__title">Saved Runs</h2>
          <div className="hint">
            Browse past runs quickly, then open one to inspect full results.
          </div>
        </div>
      </div>

      {savedRuns.length === 0 ? (
        <NoResultsYet />
      ) : (
        <>
          <div className="row" style={{ gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
            <input
              className="input"
              type="text"
              placeholder="Search by run ID or ground truth..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ flex: "1 1 320px" }}
            />

            <select
              className="input"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{ width: "220px" }}
            >
              <option value="newest">Sort: Newest first</option>
              <option value="highest-drift">Sort: Highest deviation</option>
              <option value="most-posts">Sort: Most posts</option>
            </select>
          </div>

          {visibleRuns.length === 0 ? (
            <div className="callout">No saved runs match this search.</div>
          ) : (
            visibleRuns.map((result, idx) => {
              const { run_log } = result;
              const isSelected = selectedRun?.run_log?.run_id === run_log.run_id;
              const isExpanded = expandedRunId === run_log.run_id;

              const allPosts = getAllTextPosts(run_log);
              const previewPosts = isExpanded ? allPosts : allPosts.slice(0, 2);

              const avgTD = getAvgTotalDeviation(result);
              const topDim = getTopDriftDimension(result);
              const maxGen = getMaxGenerationFromRun(run_log);
              const createdAt = formatRunTimestamp(run_log.run_id);

              return (
                <div
                  key={run_log.run_id}
                  className="history-run-card"
                  style={{
                    marginBottom: idx < visibleRuns.length - 1 ? "1.25rem" : 0,
                    padding: "1rem",
                    border: "1px solid var(--border)",
                    borderRadius: "12px",
                    background: "var(--surface-2, #fafafa)",
                  }}
                >
                  <div
                    className="row"
                    style={{
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: "1rem",
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: "260px" }}>
                      <div style={{ fontSize: "1rem", fontWeight: 700 }}>
                        {createdAt}
                      </div>

                      <div className="hint" style={{ marginTop: "0.2rem" }}>
                        {run_log.run_id}
                      </div>

                      <div className="hint" style={{ marginTop: "0.45rem" }}>
                        {run_log.agents.length} agents · {run_log.steps.length} steps · seed{" "}
                        {run_log.config?.seed ?? "—"}
                        {result.runs?.length > 1 ? ` · ${result.runs.length} parallel runs` : ""}
                      </div>

                      {isSelected && (
                        <div
                          className="pill"
                          style={{ marginTop: "0.55rem", display: "inline-block" }}
                        >
                          Currently viewing
                        </div>
                      )}
                    </div>

                    <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
                      <button
                        className="btn btn--ghost"
                        type="button"
                        onClick={() => onSelectRun(result)}
                      >
                        Open this run
                      </button>

                      <button
                        className="btn btn--ghost"
                        type="button"
                        onClick={() =>
                          setExpandedRunId(isExpanded ? null : run_log.run_id)
                        }
                      >
                        {isExpanded ? "Collapse details" : "Expand details"}
                      </button>

                      <button
                        className="btn btn--ghost btn--danger"
                        type="button"
                        onClick={() => {
                          const ok = window.confirm(
                            "Delete this saved run? This action cannot be undone."
                          );
                          if (ok) {
                            onDeleteRun(result.history_run_id);
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div
                    className="row"
                    style={{
                      gap: "0.75rem",
                      flexWrap: "wrap",
                      marginTop: "1rem",
                      marginBottom: "1rem",
                    }}
                  >
                    <div
                      style={{
                        minWidth: "160px",
                        padding: "0.75rem",
                        borderRadius: "10px",
                        background: "white",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div className="hint">Posts generated</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                        {allPosts.length}
                      </div>
                    </div>

                    <div
                      style={{
                        minWidth: "160px",
                        padding: "0.75rem",
                        borderRadius: "10px",
                        background: "white",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div className="hint">Max generation</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                        {maxGen}
                      </div>
                    </div>

                    <div
                      style={{
                        minWidth: "180px",
                        padding: "0.75rem",
                        borderRadius: "10px",
                        background: "white",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div className="hint">Avg Total Deviation</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#D85A30" }}>
                        {avgTD ?? "N/A"}
                      </div>
                    </div>

                    <div
                      style={{
                        minWidth: "220px",
                        padding: "0.75rem",
                        borderRadius: "10px",
                        background: "white",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div className="hint">Top drift dimension</div>
                      <div style={{ fontSize: "1rem", fontWeight: 700 }}>
                        {topDim}
                      </div>
                    </div>
                  </div>

                  <div style={{ marginBottom: "1rem" }}>
                    <div className="label" style={{ marginBottom: "0.35rem" }}>
                      Ground truth
                    </div>
                    <div
                      className="history-ground-truth"
                      style={isExpanded ? {} : clamp2}
                    >
                      {result.ground_truth_content}
                    </div>
                  </div>

                  <div>
                    <div className="label" style={{ marginBottom: "0.5rem" }}>
                      {isExpanded ? "All generated posts" : "Post preview"}
                    </div>

                    {previewPosts.length === 0 ? (
                      <div className="hint">No generated posts found in this run.</div>
                    ) : (
                      previewPosts.map((post) => (
                        <div
                          key={post.id}
                          style={{
                            padding: "0.75rem 0",
                            borderTop: "1px solid var(--border)",
                          }}
                        >
                          <div className="hint" style={{ marginBottom: "0.3rem" }}>
                            Step {post.step} · {post.author} · {post.action} · Gen {post.generation}
                            {isExpanded && (
                              <>
                                {" · "}Emotional {post.emotional.toFixed(2)}
                                {" · "}Controversy {post.controversy.toFixed(2)}
                                {" · "}Fringe {post.fringe.toFixed(2)}
                                {" · "}Threat {post.threat.toFixed(2)}
                              </>
                            )}
                          </div>

                          <div style={isExpanded ? {} : clamp2}>
                            {post.text}
                          </div>
                        </div>
                      ))
                    )}

                    {!isExpanded && allPosts.length > 2 && (
                      <div className="hint" style={{ marginTop: "0.5rem" }}>
                        + {allPosts.length - 2} more posts hidden
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </>
      )}
    </section>
  );
}

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
              <ErrorBar dataKey="error" direction="y" width={4} strokeWidth={2} stroke="#4a4a8a" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>
    </>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState("new");
  const [groundTruth, setGroundTruth] = useState("");
  const [_newsId, setNewsId] = useState(null);
  const [config, setConfig] = useState({
    agentCount: 3,
    steps: 3,
    seed: 42,
    intraClusterP: 0.55,
    interClusterM: 2,
    agentsPerCluster: 8,
    weakTieP: 0.05,
    simulations: 1,
  });
  const [loading, setLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [savedRuns, setSavedRuns] = useState([]);
  const [simError, setSimError] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);

  const [activeRunIndex, setActiveRunIndex] = useState(0);

  const withinLimit = groundTruth.length > 0 && groundTruth.length <= 6000;

  const configValid = 
  config.agentCount !== "" && config.agentCount > 0 &&
  config.steps !== "" && config.steps > 0 &&
  config.seed !== "" && config.seed !== null &&
  config.simulations !== "" && config.simulations > 0 &&
  config.intraClusterP !== "" &&
  config.interClusterM !== "" && config.interClusterM > 0 &&
  config.agentsPerCluster !== "" && config.agentsPerCluster > 0 &&
  config.weakTieP !== "";

  async function loadSavedRunsFromBackend() {
    try {
      const listRes = await fetch("/api/history");
      if (!listRes.ok) {
        throw new Error("Failed to load history list");
      }

      const historyList = await listRes.json();

      const detailResults = await Promise.all(
        historyList.map(async (item) => {
          const detailRes = await fetch(`/api/history/${item.run_id}`);
          if (!detailRes.ok) {
            throw new Error(`Failed to load history run ${item.run_id}`);
          }
          return detailRes.json();
        })
      );

      const restoredRuns = detailResults
        .map((item) => ({
          ...item.result_json,
          history_run_id: item.run_id,
          ground_truth_content: item.content,
        }))
        .filter((item) => item.run_log);

      setSavedRuns(restoredRuns);

      if (restoredRuns.length > 0) {
        setSelectedRun(restoredRuns[0]);
      }
    } catch (e) {
      console.error("Failed to load history:", e);
    }
  }

  useEffect(() => {
    loadSavedRunsFromBackend();
  }, []);

  async function handleDeleteRun(runId) {
    try {
      const res = await fetch(`/api/history/${runId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to delete history run");
      }

      if (selectedRun?.history_run_id === runId) {
        setSelectedRun(null);
        setSimResult(null);
      }

      await loadSavedRunsFromBackend();
    } catch (e) {
      setSimError(e.message);
    }
  }

  async function handleRun() {
    setLoading(true);
    setSimResult(null);
    setSimError(null);
    try {
      // 1. save news
      const newsRes = await fetch("/api/news", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: groundTruth }),
      });

      if (!newsRes.ok) {
        const err = await newsRes.json().catch(() => ({ detail: newsRes.statusText }));
        throw new Error(err.detail || "Failed to save news");
      }

      const newsData = await newsRes.json();
      const createdNewsId = newsData.id;
      setNewsId(createdNewsId);

      // 2. run simulation with news_id
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          news_id: createdNewsId,
          agent_count: config.agentCount,
          steps: config.steps,
          seed: config.seed,
          intra_cluster_p: config.intraClusterP,
          inter_cluster_m: config.interClusterM,
          agents_per_cluster: config.agentsPerCluster,
          weak_tie_p: config.weakTieP,
          simulations: config.simulations,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Simulation failed");
      }
      const data = await res.json();
      setSimResult(data);
      setSelectedRun(data);

      setActiveRunIndex(0);

      await loadSavedRunsFromBackend();
    } catch (e) {
      setSimError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const currentRun = selectedRun?.runs && selectedRun.runs.length > 0
    ? selectedRun.runs[activeRunIndex]
    : selectedRun;

  return (
    <div className="app">
      <Sidebar active={page} onNavigate={setPage} simResult={selectedRun} />
      <main className="main">
        <Header title="SoFake — Fake News Evolution Simulator" selectedRun={selectedRun} />
        <div className="content">

          {selectedRun?.runs && selectedRun.runs.length > 1 && ["graph", "dashboard"].includes(page) && (
            <div className="card" style={{ marginBottom: "1rem", padding: "1rem" }}>
              <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                <span className="label" style={{ margin: 0, marginRight: "1rem" }}>Select Parallel Run:</span>
                {selectedRun.runs.map((_, idx) => (
                  <button
                    key={idx}
                    className={`btn btn--ghost ${activeRunIndex === idx ? "is-active" : ""}`}
                    onClick={() => setActiveRunIndex(idx)}
                    type="button"
                  >
                    Run {idx + 1}
                  </button>
                ))}
              </div>
            </div>
          )}

          {page === "new" && (
            <>
              <GroundTruthUploader value={groundTruth} onChange={setGroundTruth} />
              <SimulationConfig config={config} setConfig={setConfig} />
              <RunActions canRun={withinLimit && configValid} loading={loading} onRun={handleRun} />
              {simError && <div className="callout callout--warn">Error: {simError}</div>}
              {simResult && (
                <div className="callout">
                  Simulation complete — view results in Graph View, Overview Dashboard, and Saved Runs.
                </div>
              )}
            </>
          )}

          {page === "graph" && <GraphView simResult={currentRun} />}

          {page === "dashboard" && <OverviewDashboard simResult={currentRun} />}

          {page === "fuse" && <FuseComparisonPage simResult={selectedRun} />}

          {page === "fuse-report" && <FuseAgentReport simResult={selectedRun} />}

          {page === "parallel-fuse" && <ParallelFusePage simResult={selectedRun} />}

          {page === "runs" && (
            <SavedRuns
              savedRuns={savedRuns}
              selectedRun={selectedRun}
              onSelectRun={(run) => {
                setSelectedRun(run);
                setSimResult(run);
                setActiveRunIndex(0);
                setPage("dashboard");
              }}
              onDeleteRun={handleDeleteRun}
            />
          )}

          {page === "about" && (
            <section className="card">
              <h2 className="card__title">About SoFake</h2>
              <p style={{ marginBottom: "1rem" }}>
                SoFake is a fake news evolution simulator built to study how truthful information
                drifts as it propagates through a simulated social network of AI agents.
              </p>
              <p style={{ marginBottom: "1rem" }}>
                Each agent has a unique personality profile based on the HEXACO model —
                varying in honesty, emotionality, conscientiousness, and more — which determines
                how they react to, reframe, and spread news posts. Over multiple simulation steps,
                a ground-truth article is seeded into the network and evolves through likes,
                retweets, quotes, and new posts.
              </p>
              <p style={{ marginBottom: "1rem" }}>
                Evolved posts are scored using the <strong>FUSE framework</strong>, which measures
                deviation from the original article across 9 linguistic and semantic dimensions:
                Sentiment Shift, New Information Introduced, Certainty Shift, Stylistic Shift,
                Temporal Shift, Perspective Deviation, Sensationalism, Source Attribution Alteration,
                and Political/Ideological Bias.
              </p>
              <p style={{ marginBottom: "1rem" }}>
                Running multiple parallel simulations allows you to compare how the same article
                drifts across different random network configurations and agent orderings,
                giving a statistical picture of misinformation spread.
              </p>
              <div className="callout" style={{ marginTop: "1rem" }}>
                SoFake does not scrape live news, detect real misinformation, or connect to any
                external data source. It is a research and educational tool only.
              </div>
            </section>
          )}

        </div>
      </main>
    </div>
  );
}