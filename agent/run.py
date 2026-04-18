"""
run.py — Simulation entry point for the newsreel misinformation ecosystem.

Wires together:
    network.py  →  social graph construction (clusters, hubs, weak ties)
    feed.py     →  per-agent feed ranking (signal + recency, personalised)
    prompts.py  →  LLM-driven agent action + post generation

Loop:
    For each step:
        1. Shuffle agents (asynchronous scheduling)
        2. Each agent gets a ranked feed of visible posts
        3. Each agent processes each feed post → action + optional new post
        4. New posts registered into PostRegistry immediately (other agents
           in the same step can see them if they're scheduled later)
        5. Signal drift logged per new post

Output:
    - Console: step-by-step summary
    - <run_id>/run_log.json: full structured log
    - <run_id>/signal_drift.json: per-post signal evolution across generations

Usage:
    python run.py                            # defaults: 20 agents, 7 steps
    python run.py --agents 30 --steps 10    
    python run.py --seed 42 --out my_run    
"""

import os
import sys
import json
import random
import argparse
import uuid
import time #new
from datetime import datetime
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structs import Agent, HEXACOProfile, Post, PostSignals
from network import build_network, NetworkConfig
from feed import PostRegistry, build_feed
from prompts import agent_process_post, get_post_signals, classify_post_signals


# ── Ground Truth ───────────────────────────────────────────────────────────────

GROUND_TRUTH = """
Scientists at a major US university have published a study suggesting that
microplastics found in common bottled water brands may be interfering with
human hormone regulation. The study, which tracked 3,000 participants over
5 years, found a statistically significant correlation between bottled water
consumption and disrupted cortisol and thyroid levels. The lead researcher
stated the findings are 'concerning but not yet conclusive'. Health authorities
have not yet issued any official guidance in response to the study.
""".strip()


# ── Agent Names ────────────────────────────────────────────────────────────────

NAMES = [
    "Alex","Blake","Casey","Dana","Eden","Finn","Gray","Harper",
    "Indigo","Jordan","Kai","Lane","Morgan","Nova","Oakley","Parker",
    "Quinn","Reese","Sage","Taylor","Uma","Vale","Wren","Xen",
    "Yael","Zion","Arlo","Bree","Cleo","Drew",
]


# ── Setup ──────────────────────────────────────────────────────────────────────

def make_agents(n: int) -> list[Agent]:
    import math
    names = (NAMES * math.ceil(n / len(NAMES)))[:n]
    return [
        Agent(id=i, name=names[i], profile=HEXACOProfile.random())
        for i in range(n)
    ]


def seed_ground_truth(network, registry: PostRegistry) -> Post:
    """
    Classify the ground truth story and seed it into every cluster hub's
    post history so it appears in their neighbours' feeds from step 1.
    """
    print("  Classifying ground truth signals…")
    signals = classify_post_signals(
        post_text=GROUND_TRUTH,
        generation=0,
        source_post_id="ground_truth",
    )

    seed_post = Post(
        id="ground_truth",
        author_id="system",
        text=GROUND_TRUTH,
        signals=signals,
        parent_id=None,
    )

    # Register once per hub so it's visible from all clusters immediately
    for hub in network.hubs.values():
        registry.add(seed_post, hub.id)

    print(f"  Ground truth seeded into {len(network.hubs)} cluster hubs")
    print(f"  Signals → emotional_charge={signals.emotional_charge:.2f}  "
          f"controversy={signals.controversy:.2f}  "
          f"fringe_score={signals.fringe_score:.2f}  "
          f"threat_level={signals.threat_level:.2f}")
    return seed_post


# ── Logging Helpers ────────────────────────────────────────────────────────────

def signals_dict(s: PostSignals) -> dict:
    return {
        "emotional_charge": round(s.emotional_charge, 4),
        "controversy":      round(s.controversy, 4),
        "fringe_score":     round(s.fringe_score, 4),
        "threat_level":     round(s.threat_level, 4),
        "generation":       s.generation,
        "source_post_id":   s.source_post_id,
    }


def agent_dict(agent: Agent, cluster_id: int, is_hub: bool) -> dict:
    p = agent.profile
    return {
        "id":        agent.id,
        "name":      agent.name,
        "cluster":   cluster_id,
        "is_hub":    is_hub,
        "profile": {
            "honesty_humility":  round(p.honesty_humility, 4),
            "emotionality":      round(p.emotionality, 4),
            "extraversion":      round(p.extraversion, 4),
            "agreeableness":     round(p.agreeableness, 4),
            "conscientiousness": round(p.conscientiousness, 4),
            "openness":          round(p.openness, 4),
        },
    }


# ── Console Formatting ─────────────────────────────────────────────────────────

ACTION_ICONS = {
    "like":        "♥",
    "retweet":     "↺",
    "quote_tweet": "❝",
    "comment":     "💬",
    "new_post":    "✍",
    "report":      "⚑",
    "ignore":      "·",
}

def print_step_header(step: int, n_steps: int):
    print(f"\n{'═' * 60}")
    print(f"  STEP {step} / {n_steps}")
    print(f"{'═' * 60}")

def print_agent_action(agent: Agent, action: str, post: Post, new_post: Post | None):
    icon = ACTION_ICONS.get(action, "?")
    print(f"  {icon}  {agent.name:<10} {action:<12} ← \"{post.text[:50]}…\"")
    if new_post:
        print(f"      └─ posted: \"{new_post.text[:80]}…\"")
        s = new_post.signals
        print(f"         signals: ec={s.emotional_charge:.2f} "
              f"ct={s.controversy:.2f} "
              f"fr={s.fringe_score:.2f} "
              f"tl={s.threat_level:.2f} "
              f"(gen {s.generation})")

def print_step_summary(step_log: dict):
    actions = [e["action"] for e in step_log["events"]]
    counts = {}
    for a in actions:
        counts[a] = counts.get(a, 0) + 1
    total_posts = step_log["new_posts_this_step"]
    print(f"\n  ── Step summary: {len(actions)} actions, {total_posts} new posts")
    for action, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"     {ACTION_ICONS.get(action,'?')} {action}: {n}")


# ── Core Simulation Loop ───────────────────────────────────────────────────────

def run_simulation(
    n_agents: int,
    n_steps: int,
    seed: int | None,
    out_dir: str,
    ground_truth: str = None,
    run_identifier: str = "", #new
    intra_cluster_p: float = 0.5,
    inter_cluster_m: int = 2,
    agents_per_cluster: int = 10,
    weak_tie_p: float = 0.05,
    n_simulations: int = 1,
) -> tuple[dict, dict]:
    if seed is not None:
        random.seed(seed)

    if ground_truth is None:
        ground_truth = GROUND_TRUTH   # falls back to the hardcoded one

    #Modified
    base_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{base_id}_{run_identifier}" if run_identifier else base_id

    out_path = os.path.join(out_dir, run_id)
    os.makedirs(out_path, exist_ok=True)

    print(f"\n{'═' * 60}")
    # [MODIFIED]
    print(f"  NEWSREEL SIMULATION [ID: {run_identifier}]")
    print(f"  run_id={run_id}  agents={n_agents}  steps={n_steps}  seed={seed}")
    print(f"{'═' * 60}\n")

    # ── Build world ────────────────────────────────────────────────────────────
    print("Building agents…")
    agents = make_agents(n_agents)
    agent_map = {a.id: a for a in agents}

    print("Building network…")
    config  = NetworkConfig(
        followback_p= intra_cluster_p,
        inter_cluster_m=inter_cluster_m,
        agents_per_cluster=agents_per_cluster,
        p_weak=weak_tie_p,
    )
    network = build_network(agents, config)
    hub_ids = {hub.id for hub in network.hubs.values()}

    print(f"\n{network.summary()}\n")

    registry = PostRegistry()

    print("Seeding ground truth…")
    seed_post = seed_ground_truth(network, registry)

    # ── Run log structure ──────────────────────────────────────────────────────
    run_log = {
        "run_id":    run_id,
        "timestamp": datetime.now().isoformat(),
        "config": {
            "n_agents":           n_agents,
            "n_steps":            n_steps,
            "seed":               seed,
            "followback_p":    config.followback_p,
            "inter_cluster_m":    config.inter_cluster_m,
            "agents_per_cluster": config.agents_per_cluster,
        },
        "agents":  [
            agent_dict(a, network.agent_cluster[a.id], a.id in hub_ids)
            for a in agents
        ],
        "network": {
            "n_nodes":    network.graph.number_of_nodes(),
            "n_edges":    network.graph.number_of_edges(),
            "n_clusters": len(network.clusters),
            "avg_degree": round(
                network.graph.number_of_edges() / max(network.graph.number_of_nodes(), 1), 2
            ),
            "hubs": {str(cid): h.name for cid, h in network.hubs.items()},
        },
        "ground_truth": {
            "text":    ground_truth,
            "signals": signals_dict(seed_post.signals),
        },
        "steps": [],
    }

    # signal_drift: post_id -> list of signal snapshots across generations
    # Tracks the lineage of every post that spawns from the ground truth
    signal_drift: dict[str, list[dict]] = {
        "ground_truth": [signals_dict(seed_post.signals)]
    }

    post_counter = 0  # for generating unique post IDs

    # ── Step loop ──────────────────────────────────────────────────────────────
    for step in range(1, n_steps + 1):
        print_step_header(step, n_steps)

        step_log = {
            "step":               step,
            "agent_order":        [],
            "events":             [],
            "new_posts_this_step": 0,
        }

        # Asynchronous scheduling: shuffle agents each step
        shuffled = agents[:]
        random.shuffle(shuffled)
        step_log["agent_order"] = [a.id for a in shuffled]

        for agent in shuffled:
            feed = build_feed(agent, network, registry)

            if not feed:
                continue

            for post in feed:
                action_result = agent_process_post(agent, post, ground_truth)
                action = action_result.action

                new_post = None
                if action_result.text:
                    # Classify signals for the new post
                    new_signals = get_post_signals(action, action_result.text, post)

                    post_counter += 1
                    new_post = Post(
                        id=f"post_{post_counter}",
                        author_id=str(agent.id),
                        text=action_result.text,
                        signals=new_signals,
                        parent_id=post.id,
                    )

                    # Register immediately — later agents this step can see it
                    registry.add(new_post, agent.id)
                    step_log["new_posts_this_step"] += 1

                    # Track signal drift from this post's lineage
                    lineage_key = new_signals.source_post_id
                    if lineage_key not in signal_drift:
                        signal_drift[lineage_key] = []
                    signal_drift[lineage_key].append({
                        "post_id":    new_post.id,
                        "author":     agent.name,
                        "step":       step,
                        **signals_dict(new_signals),
                    })

                print_agent_action(agent, action, post, new_post)

                # Log the event
                event = {
                    "agent_id":      agent.id,
                    "agent_name":    agent.name,
                    "action":        action,
                    "source_post_id": post.id,
                    "new_post_id":   new_post.id if new_post else None,
                    "new_post_text": new_post.text if new_post else None,
                    "new_signals":   signals_dict(new_post.signals) if new_post else None,
                }
                step_log["events"].append(event)

        print_step_summary(step_log)
        run_log["steps"].append(step_log)

    # ── Write outputs ──────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  Simulation complete — writing output to {out_path}/")

    run_log_path = os.path.join(out_path, "run_log.json")
    with open(run_log_path, "w") as f:
        json.dump(run_log, f, indent=2)
    print(f"  ✓  run_log.json       ({len(run_log['steps'])} steps, "
          f"{sum(s['new_posts_this_step'] for s in run_log['steps'])} new posts)")

    drift_path = os.path.join(out_path, "signal_drift.json")
    with open(drift_path, "w") as f:
        json.dump(signal_drift, f, indent=2)
    print(f"  ✓  signal_drift.json  ({len(signal_drift)} lineage chains tracked)")

    print(f"{'═' * 60}\n")

    return run_log, signal_drift


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run the newsreel simulation.")
    parser.add_argument("--agents", type=int, default=20,   help="Number of agents (default 20)")
    parser.add_argument("--steps",  type=int, default=7,    help="Number of steps (default 7)")
    parser.add_argument("--seed",   type=int, default=None, help="Random seed")
    parser.add_argument("--out",    type=str, default="runs", help="Output directory (default: runs/)")

    # [NEW]
    parser.add_argument("--sim-count", type=int, default=1, help="Parallel Simulation")
    args = parser.parse_args()


    keys_str = os.getenv("GROQ_API_KEY", "")

    API_KEYS = [k.strip() for k in keys_str.split(",") if k.strip()]

    if not API_KEYS:
        print("❌ Error: No GROQ_API_KEYS found in .env. Please make sure all set up。")
        sys.exit(1)

    if args.sim_count > 1:
        print(f"🚀 Ready to perform {args.sim_count} number of simulations...")
        pids = []

        for i in range(args.sim_count):
            current_key = API_KEYS[i % len(API_KEYS)]

            pid = os.fork()

            if pid == 0:  # child
                os.environ["GROQ_API_KEY"] = current_key

                log_dir = os.path.join(args.out, "logs")
                os.makedirs(log_dir, exist_ok=True)
                log_file = open(f"{log_dir}/run_{i:02d}.log", "w")
                os.dup2(log_file.fileno(), sys.stdout.fileno())
                os.dup2(log_file.fileno(), sys.stderr.fileno())

                child_seed = (args.seed + i) if args.seed is not None else None

                run_simulation(
                    n_agents=args.agents,
                    n_steps=args.steps,
                    seed=child_seed,
                    out_dir=args.out,
                    run_identifier=f"run{i:02d}"
                )

                sys.exit(0)

            else: # parent
                pids.append(pid)
                print(f"  - Instance {i} started (PID: {pid}), Using Key: {current_key[:10]}...")
                time.sleep(0.5)

        for pid in pids:
            os.waitpid(pid, 0)
        print("\n✅ All simulations have finished！")

    else:
        # single simulation
        os.environ["GROQ_API_KEY"] = API_KEYS[0]
        run_simulation(
            n_agents=args.agents,
            n_steps=args.steps,
            seed=args.seed,
            out_dir=args.out
        )

if __name__ == "__main__":
    main()
