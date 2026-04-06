from __future__ import annotations
"""
network.py — Social network graph for the newsreel simulation.

Topology: Hybrid
  - Intra-cluster: dense Erdős–Rényi subgraphs
  - Inter-cluster: scale-free preferential attachment (Barabási–Albert style)

Design choices:
  - Number of clusters scales with agent count (~1 per 10 agents)
  - Cluster membership is biased by agent extraversion (extraverts attract more)
  - Each cluster has one hub agent (highest extraversion) who seeds the ground truth
  - Edges are undirected and unweighted
"""

import random
import math
import networkx as nx
from dataclasses import dataclass, field
from structs import Agent, HEXACOProfile


# ── Network Config ─────────────────────────────────────────────────────────────

@dataclass
class NetworkConfig:
    intra_cluster_p: float = 0.6      # Edge probability within a cluster
    inter_cluster_m: int = 2          # Edges each cluster hub forms to other hubs (BA-style)
    agents_per_cluster: int = 10      # Controls how many clusters are created


# ── Cluster Assignment ─────────────────────────────────────────────────────────

def assign_clusters(agents: list[Agent], agents_per_cluster: int) -> dict[int, list[Agent]]:
    """
    Assign agents to clusters biased by extraversion.

    High-extraversion agents are more likely to end up in larger, more
    connected clusters. Implemented by weighting cluster selection during
    assignment: each cluster accretes agents proportionally to the mean
    extraversion of its current members (rich-get-richer within clusters).

    Returns a dict mapping cluster_id -> list of Agent.
    """
    n_clusters = max(2, math.ceil(len(agents) / agents_per_cluster))

    # Sort agents by extraversion descending so each cluster seeds with a
    # high-extraversion anchor first
    sorted_agents = sorted(agents, key=lambda a: a.profile.extraversion, reverse=True)

    clusters: dict[int, list[Agent]] = {i: [] for i in range(n_clusters)}

    # Seed one anchor per cluster
    for i in range(n_clusters):
        if i < len(sorted_agents):
            clusters[i].append(sorted_agents[i])

    remaining = sorted_agents[n_clusters:]

    for agent in remaining:
        # Weight each cluster by its mean extraversion (or 0.5 if empty)
        weights = []
        for cid, members in clusters.items():
            if members:
                mean_ext = sum(m.profile.extraversion for m in members) / len(members)
            else:
                mean_ext = 0.5
            weights.append(mean_ext)

        chosen = random.choices(list(clusters.keys()), weights=weights, k=1)[0]
        clusters[chosen].append(agent)

    # Remove any empty clusters
    clusters = {cid: members for cid, members in clusters.items() if members}

    return clusters


# ── Graph Construction ─────────────────────────────────────────────────────────

def build_intra_cluster_edges(
    G: nx.Graph,
    cluster_members: list[Agent],
    p: float,
) -> None:
    """
    Add dense Erdős–Rényi edges within a single cluster.
    Each pair of agents within the cluster is connected with probability p.
    """
    for i, a in enumerate(cluster_members):
        for b in cluster_members[i + 1:]:
            if random.random() < p:
                G.add_edge(a.id, b.id)


def get_cluster_hub(cluster_members: list[Agent]) -> Agent:
    """
    Return the agent with the highest extraversion in a cluster.
    This agent acts as the cluster's hub and story seed point.
    """
    return max(cluster_members, key=lambda a: a.profile.extraversion)


def build_inter_cluster_edges(
    G: nx.Graph,
    clusters: dict[int, list[Agent]],
    m: int,
) -> None:
    """
    Connect cluster hubs using preferential attachment (BA-style).

    Each hub connects to m other hubs, with probability proportional to
    their current degree (or 1 if degree is 0). This creates a scale-free
    topology at the inter-cluster level.
    """
    hubs = [get_cluster_hub(members) for members in clusters.values()]

    if len(hubs) < 2:
        return

    # Start with the first two hubs connected
    connected = [hubs[0], hubs[1]]
    G.add_edge(hubs[0].id, hubs[1].id)

    for hub in hubs[2:]:
        # Preferential attachment weights by degree
        weights = [max(G.degree(h.id), 1) for h in connected]
        targets = random.choices(connected, weights=weights, k=min(m, len(connected)))
        targets = list({t.id: t for t in targets}.values())  # deduplicate
        for target in targets:
            if not G.has_edge(hub.id, target.id):
                G.add_edge(hub.id, target.id)
        connected.append(hub)


# ── Public API ─────────────────────────────────────────────────────────────────

@dataclass
class SocialNetwork:
    graph: nx.Graph
    clusters: dict[int, list[Agent]]       # cluster_id -> agents
    hubs: dict[int, Agent]                 # cluster_id -> hub agent (story seed)
    agent_cluster: dict[int, int]          # agent_id -> cluster_id

    def neighbours(self, agent_id: int) -> list[int]:
        """Return neighbour agent IDs for a given agent."""
        return list(self.graph.neighbors(agent_id))

    def get_cluster_of(self, agent_id: int) -> int:
        return self.agent_cluster[agent_id]

    def summary(self) -> str:
        n_nodes = self.graph.number_of_nodes()
        n_edges = self.graph.number_of_edges()
        n_clusters = len(self.clusters)
        avg_degree = (2 * n_edges / n_nodes) if n_nodes else 0
        hub_names = {cid: h.name for cid, h in self.hubs.items()}
        lines = [
            f"Nodes:        {n_nodes}",
            f"Edges:        {n_edges}",
            f"Clusters:     {n_clusters}",
            f"Avg degree:   {avg_degree:.2f}",
            f"Cluster hubs: {hub_names}",
        ]
        return "\n".join(lines)


def build_network(agents: list[Agent], config: NetworkConfig | None = None) -> SocialNetwork:
    """
    Build the hybrid social network from a list of agents.

    Steps:
      1. Assign agents to clusters (extraversion-biased)
      2. Add dense intra-cluster edges (Erdős-Rényi)
      3. Connect cluster hubs with scale-free inter-cluster edges (BA)

    Returns a SocialNetwork with the graph, cluster map, and hub index.
    """
    if config is None:
        config = NetworkConfig()

    G = nx.Graph()

    # Add all agents as nodes, storing profile metadata
    for agent in agents:
        G.add_node(agent.id, name=agent.name, extraversion=agent.profile.extraversion)

    # Assign to clusters
    clusters = assign_clusters(agents, config.agents_per_cluster)

    # Intra-cluster edges
    for members in clusters.values():
        build_intra_cluster_edges(G, members, config.intra_cluster_p)

    # Inter-cluster edges via hub preferential attachment
    build_inter_cluster_edges(G, clusters, config.inter_cluster_m)

    # Index: agent_id -> cluster_id
    agent_cluster: dict[int, int] = {}
    for cid, members in clusters.items():
        for agent in members:
            agent_cluster[agent.id] = cid

    # Index: cluster_id -> hub agent
    hubs = {cid: get_cluster_hub(members) for cid, members in clusters.items()}

    return SocialNetwork(
        graph=G,
        clusters=clusters,
        hubs=hubs,
        agent_cluster=agent_cluster,
    )
