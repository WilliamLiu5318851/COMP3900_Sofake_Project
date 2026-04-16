"""
network.py — Social network graph for the newsreel simulation.

Topology: Directed hybrid
  - Hubs: top-N agents by extraversion globally (N ≈ total / agents_per_cluster)
  - Agent → hub following: each agent follows hubs with probability proportional
    to cosine similarity of their HEXACO profiles
  - Hub → agent follow-back: each hub follows back the top-K followers ranked by
    extraversion, where K = ceil(0.1 * |top-extraversion decile of that hub's
    followers|). Hubs are selective — they only follow a fraction of high-
    extraversion followers back.
  - Hub ↔ hub edges: mutual (both directions added), scale-free BA-style
  - Weak ties: directed, extraversion-weighted, skipping hub-hub pairs

Graph type: nx.DiGraph
  - Edge A → B means "A follows B" (A sees B's posts)
  - Feed visibility: 2-hop successor walk (you see posts from people you follow,
    and from people they follow)

SocialNetwork fields:
  - clusters:      hub_id -> list[Agent] who follow that hub (for logging/viz)
  - hubs:          hub_id -> Agent  (hub_id == agent.id for global hubs)
  - agent_cluster: agent_id -> hub_id of their most-similar hub (primary hub)
"""

import math
import random
import networkx as nx
from dataclasses import dataclass, field
from structs import Agent
from prompts import *


# ── Network Config ─────────────────────────────────────────────────────────────

@dataclass
class NetworkConfig:
    agents_per_cluster: int = 10   # Controls how many hubs are elected
    inter_cluster_m: int   = 2     # BA-style edges per hub to other hubs
    p_weak: float          = 0.02  # Base probability of weak tie edges
    followback_p: float    = 0.1   # Probability of hub following back its followers (in build_agent_hub_edges)
    intra_cluster_p: float = 0.5   # Probability of edges between agents in the same cluster (in build_intra_cluster_edges)


# ── HEXACO Cosine Similarity ───────────────────────────────────────────────────

def _profile_vec(agent: Agent) -> list[float]:
    p = agent.profile
    return [
        p.honesty_humility,
        p.emotionality,
        p.extraversion,
        p.agreeableness,
        p.conscientiousness,
        p.openness,
    ]


def cosine_similarity(a: Agent, b: Agent) -> float:
    """
    Cosine similarity between two agents' HEXACO profiles.
    Returns a value in [0, 1] (profiles are non-negative, so dot ≥ 0).
    A score of 1.0 = identical trait vector; 0.0 = orthogonal.
    """
    va = _profile_vec(a)
    vb = _profile_vec(b)
    dot  = sum(x * y for x, y in zip(va, vb))
    norm_a = math.sqrt(sum(x * x for x in va))
    norm_b = math.sqrt(sum(x * x for x in vb))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Hub Election ───────────────────────────────────────────────────────────────

def elect_hubs(agents: list[Agent], agents_per_cluster: int) -> list[Agent]:
    """
    Elect the top-N agents by extraversion as global hubs.
    N = ceil(total_agents / agents_per_cluster), minimum 2.

    These agents are the broadcast anchors of the network — they seed the
    ground truth and gain followers based on profile similarity.
    """
    n_hubs = max(2, math.ceil(len(agents) / agents_per_cluster))
    sorted_by_ext = sorted(agents, key=lambda a: a.profile.extraversion, reverse=True)
    return sorted_by_ext[:n_hubs]


# ── Agent → Hub Following ──────────────────────────────────────────────────────

def build_agent_hub_edges(
    G: nx.DiGraph,
    agents: list[Agent],
    hubs: list[Agent],
) -> dict[int, list[Agent]]:
    """
    Each non-hub agent independently decides which hubs to follow.

    For each hub, an agent's follow probability is proportional to their
    cosine similarity to that hub (softmax-style over the hub set):

        P(agent follows hub_i) = sim(agent, hub_i) / sum(sim(agent, hub_j))

    Each hub is sampled independently using that probability, so an agent
    can follow zero, one, or all hubs. This creates overlapping soft
    communities rather than hard cluster assignments.

    Returns hub_id -> list[Agent] mapping (agents who follow that hub).
    """
    hub_ids = {h.id for h in hubs}
    hub_followers: dict[int, list[Agent]] = {h.id: [] for h in hubs}

    for agent in agents:
        if agent.id in hub_ids:
            continue  # hubs don't follow themselves via this mechanism

        sims = [cosine_similarity(agent, hub) for hub in hubs]
        total_sim = sum(sims)
        
        # Agent always follows the most similar hub
        best_hub_idx = max(range(len(hubs)), key=lambda i: sims[i])
        best_hub = hubs[best_hub_idx]
        G.add_edge(agent.id, best_hub.id)
        hub_followers[best_hub.id].append(agent)
        
        # Agent has a chance to follow other hubs with probability proportional to similarity
        for i, hub in enumerate(hubs):
            if i == best_hub_idx:
                continue  # already following best hub
            p_follow = (sims[i] / total_sim) if total_sim > 0 else 0
            if random.random() < p_follow:
                G.add_edge(agent.id, hub.id)
                hub_followers[hub.id].append(agent)
    return hub_followers

def build_intra_cluster_edges(
    G: nx.DiGraph,
    hub_followers: dict[int, list[Agent]],
    intra_cluster_p: float,
) -> None:
    """
    Add directed edges between agents within the same hub community.

    For each hub, we consider all pairs of its followers (A, B). For each
    pair, we add a directed edge A → B with probability p_followback, and
    independently add B → A with the same probability. This creates a
    denser local neighborhood around each hub, simulating follow-back and
    local clustering within communities.

    This step is separate from the selective hub follow-back (which adds
    edges from hubs to their top extraverted followers) to allow for more
    flexible intra-community connectivity.
    """
    for followers in hub_followers.values():
        for i, agent_a in enumerate(followers):
            for agent_b in followers[i + 1:]:
                if random.random() < intra_cluster_p:
                    G.add_edge(agent_a.id, agent_b.id)
                if random.random() < intra_cluster_p:
                    G.add_edge(agent_b.id, agent_a.id)

# ── Hub → Agent Follow-back ────────────────────────────────────────────────────

def build_hub_followback_edges(
    G: nx.DiGraph,
    hub: Agent,
    followers: list[Agent],
) -> None:
    """
    Each hub follows back a selective subset of its followers.

    The follow-back quota K is based on the top extraversion decile of the
    hub's follower pool:

        top_decile  = ceil(0.1 * len(followers))  agents with highest extraversion
        K           = ceil(0.1 * top_decile)

    The hub then follows back the top-K of those high-extraversion followers.
    This means hubs preferentially amplify the most extraverted agents who
    are already in their audience — a rich-get-richer dynamic on follow-back.

    If the follower pool is empty, no edges are added.
    """
    if not followers:
        return

    # Rank followers by extraversion descending
    ranked = sorted(followers, key=lambda a: a.profile.extraversion, reverse=True)

    top_decile_count = max(1, math.ceil(0.1 * len(ranked)))
    k = max(1, math.ceil(0.1 * top_decile_count))

    for followee in ranked[:k]:
        G.add_edge(hub.id, followee.id)   # hub follows back


# ── Hub ↔ Hub Edges (mutual BA-style) ─────────────────────────────────────────

def build_inter_hub_edges(
    G: nx.DiGraph,
    hubs: list[Agent],
    m: int,
) -> None:
    """
    Connect hubs to each other using preferential attachment (BA-style).
    Edges are mutual (both A→B and B→A), since hubs are presumed to follow
    each other. Degree used for attachment weight is total degree (in + out).

    Starting pair is seeded, then each subsequent hub attaches to m existing
    hubs weighted by their current degree.
    """
    if len(hubs) < 2:
        return

    def add_mutual(a: Agent, b: Agent) -> None:
        if not G.has_edge(a.id, b.id):
            G.add_edge(a.id, b.id)
        if not G.has_edge(b.id, a.id):
            G.add_edge(b.id, a.id)

    connected = [hubs[0], hubs[1]]
    add_mutual(hubs[0], hubs[1])

    for hub in hubs[2:]:
        weights = [max(G.degree(h.id), 1) for h in connected]
        targets = random.choices(connected, weights=weights, k=min(m, len(connected)))
        targets = list({t.id: t for t in targets}.values())
        for target in targets:
            add_mutual(hub, target)
        connected.append(hub)


# ── Weak Tie Edges (directed, extraversion-weighted) ──────────────────────────

def build_weak_tie_edges(
    G: nx.DiGraph,
    hub_followers: dict[int, list[Agent]],
    hub_ids: set[int],
    p_weak: float,
) -> None:
    """
    Add sparse directed weak ties between agents in different hub communities.

    For each cross-community agent pair (A from community i, B from community j),
    two independent Bernoulli trials determine whether A→B and B→A exist:

        P(A follows B) = p_weak * A.extraversion * B.extraversion

    Hub-hub pairs are skipped (already handled by inter-hub edges).
    Agents who share a community (follow the same hub) are also skipped to
    avoid redundant within-community edges.

    This emulates Granovetter weak ties — occasional cross-community bridges
    driven by individual extraversion rather than structural position.
    """
    community_ids = list(hub_followers.keys())

    for i, hub_a in enumerate(community_ids):
        for hub_b in community_ids[i + 1:]:
            for agent_a in hub_followers[hub_a]:
                for agent_b in hub_followers[hub_b]:
                    if agent_a.id in hub_ids and agent_b.id in hub_ids:
                        continue

                    p_ab = p_weak * agent_a.profile.extraversion * agent_b.profile.extraversion
                    p_ba = p_weak * agent_b.profile.extraversion * agent_a.profile.extraversion

                    if random.random() < p_ab:
                        G.add_edge(agent_a.id, agent_b.id)
                    if random.random() < p_ba:
                        G.add_edge(agent_b.id, agent_a.id)


# ── Public API ─────────────────────────────────────────────────────────────────

@dataclass
class SocialNetwork:
    graph: nx.DiGraph
    clusters: dict[int, list[Agent]]   # hub_id -> agents who follow that hub
    hubs: dict[int, Agent]             # hub_id -> Agent (hub_id == agent.id)
    agent_cluster: dict[int, int]      # agent_id -> primary hub_id (most similar)

    def successors(self, agent_id: int) -> list[int]:
        """Agents that agent_id follows (successor nodes in DiGraph)."""
        return list(self.graph.successors(agent_id))

    def predecessors(self, agent_id: int) -> list[int]:
        """Agents that follow agent_id (predecessor nodes in DiGraph)."""
        return list(self.graph.predecessors(agent_id))

    def get_cluster_of(self, agent_id: int) -> int:
        return self.agent_cluster[agent_id]

    def summary(self) -> str:
        n_nodes   = self.graph.number_of_nodes()
        n_edges   = self.graph.number_of_edges()
        n_hubs    = len(self.hubs)
        avg_out   = (n_edges / n_nodes) if n_nodes else 0
        hub_names = {hid: h.name for hid, h in self.hubs.items()}
        lines = [
            f"Nodes:        {n_nodes}",
            f"Directed edges: {n_edges}",
            f"Hubs:         {n_hubs}",
            f"Avg out-degree: {avg_out:.2f}",
            f"Hubs:         {hub_names}",
        ]
        return "\n".join(lines)


def build_network(agents: list[Agent], config: NetworkConfig | None = None) -> SocialNetwork:
    """
    Build the directed hybrid social network from a list of agents.

    Steps:
      1. Elect hubs globally by extraversion
      2. Each non-hub agent follows hubs with probability ∝ cosine similarity
      3. Each hub follows back its top-K high-extraversion followers
      4. Connect hubs mutually using BA-style preferential attachment
      5. Add sparse directed weak ties between cross-community agents

    Returns a SocialNetwork (DiGraph) with hub index, community map, and
    primary-hub assignment per agent.
    """
    if config is None:
        config = NetworkConfig()

    G = nx.DiGraph()

    for agent in agents:
        G.add_node(agent.id, name=agent.name, extraversion=agent.profile.extraversion)

    # 0. Elect hubs
    hubs = elect_hubs(agents, config.agents_per_cluster)
    hub_ids = {h.id for h in hubs}
    hub_map = {h.id: h for h in hubs}

    # 1 Agent → hub following (cosine similarity weighted)
    hub_followers = build_agent_hub_edges(G, agents, hubs)

    # 2. agent -> agent edges within each hub community (intra-cluster follow-back)
    build_intra_cluster_edges(G, hub_followers, config.followback_p)

    # 3. Hub → agent follow-back (selective, top-extraversion followers)
    for hub in hubs:
        build_hub_followback_edges(G, hub, hub_followers[hub.id])

    # 4. Hub ↔ hub mutual edges (BA preferential attachment)
    build_inter_hub_edges(G, hubs, config.inter_cluster_m)

    # 5. Directed weak ties between cross-community agents
    build_weak_tie_edges(G, hub_followers, hub_ids, config.p_weak)

    # Primary hub: most similar hub for each agent (for logging/viz)
    agent_cluster: dict[int, int] = {}
    for agent in agents:
        if agent.id in hub_ids:
            agent_cluster[agent.id] = agent.id  # hubs are their own primary
        else:
            best_hub = max(hubs, key=lambda h: cosine_similarity(agent, h))
            agent_cluster[agent.id] = best_hub.id

    return SocialNetwork(
        graph=G,
        clusters=hub_followers,
        hubs=hub_map,
        agent_cluster=agent_cluster,
    )
