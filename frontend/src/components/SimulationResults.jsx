import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function SimulationResults({ runLog }) {
  if (!runLog) return null;

  const allEvents = runLog.steps.flatMap(s => s.events);
  const newPosts = allEvents.filter(e => e.new_signals);

  // Posts per step
  const stepData = runLog.steps.map(s => ({
    name: `Step ${s.step}`,
    posts: s.new_posts_this_step,
  }));

  // Actions breakdown
  const actionCounts = {};
  allEvents.forEach(e => { actionCounts[e.action] = (actionCounts[e.action] || 0) + 1; });
  const actionData = Object.entries(actionCounts).map(([action, count]) => ({ action, count }));

  // Signal drift by generation
  const genMap = {};
  const gt = runLog.ground_truth.signals;
  genMap[0] = { ec: gt.emotional_charge, ct: gt.controversy, fr: gt.fringe_score, tl: gt.threat_level };
  newPosts.forEach(e => {
    const g = e.new_signals.generation;
    if (!genMap[g]) genMap[g] = { ec: [], ct: [], fr: [], tl: [] };
    if (Array.isArray(genMap[g].ec)) {
      genMap[g].ec.push(e.new_signals.emotional_charge);
      genMap[g].ct.push(e.new_signals.controversy);
      genMap[g].fr.push(e.new_signals.fringe_score);
      genMap[g].tl.push(e.new_signals.threat_level);
    }
  });
  const avg = arr => Array.isArray(arr) ? arr.reduce((s, v) => s + v, 0) / arr.length : arr;
  const driftData = Object.keys(genMap).sort((a,b)=>a-b).map(g => ({
    gen: `Gen ${g}`,
    emotional_charge: +avg(genMap[g].ec).toFixed(2),
    controversy: +avg(genMap[g].ct).toFixed(2),
    fringe_score: +avg(genMap[g].fr).toFixed(2),
    threat_level: +avg(genMap[g].tl).toFixed(2),
  }));

  return (
    <div>
      <h2>Simulation Results</h2>

      {/* Posts per step */}
      <h3>Posts per step</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={stepData}>
          <XAxis dataKey="name" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="posts" fill="#1D9E75" radius={[4,4,0,0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Actions breakdown */}
      <h3>Actions breakdown</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={actionData}>
          <XAxis dataKey="action" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" fill="#7F77DD" radius={[4,4,0,0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Signal drift */}
      <h3>Signal drift across generations</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={driftData}>
          <XAxis dataKey="gen" />
          <YAxis domain={[0, 1]} />
          <Tooltip />
          <Legend />
          <Line dataKey="emotional_charge" stroke="#BA7517" dot={true} />
          <Line dataKey="controversy" stroke="#7F77DD" dot={true} />
          <Line dataKey="fringe_score" stroke="#D85A30" dot={true} />
          <Line dataKey="threat_level" stroke="#E24B4A" dot={true} />
        </LineChart>
      </ResponsiveContainer>

      {/* Post timeline */}
      <h3>Post timeline</h3>
      {runLog.steps.flatMap(s => s.events.filter(e => e.new_signals).map(e => (
        <div key={e.new_post_id} style={{ border: '1px solid #eee', borderRadius: 8, padding: 12, marginBottom: 8 }}>
          <strong>{e.agent_name}</strong> · {e.action} · Gen {e.new_signals.generation}
          <p style={{ fontSize: 13, margin: '6px 0' }}>{e.new_post_text}</p>
          <small>EC {e.new_signals.emotional_charge.toFixed(2)} · CT {e.new_signals.controversy.toFixed(2)} · FR {e.new_signals.fringe_score.toFixed(2)} · TL {e.new_signals.threat_level.toFixed(2)}</small>
        </div>
      )))}
    </div>
  );
}