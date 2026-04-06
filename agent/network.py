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

import math
import random
from dataclasses import dataclass

import networkx as nx

from structs import Agent


# ── Network Config ─────────────────────────────────────────────────────────────

@dataclass
class NetworkConfig:
    intra_cluster_p: float = 0.6   # Edge probability within a cluster
    inter_cluster_m: int = 2       # Edges each hub forms to existing hubs (BA-style)
    agents_per_cluster: int = 10   # Target cluster size; controls cluster count


# ── Cluster Assignment ─────────────────────────────────────────────────────────

def assign_clusters(agents: list[Agent], agents_per_cluster: int) -> dict[int, list[Agent]]:
    """
    Assign agents to clusters biased by extraversion.

    High-extraversion agents are more likely to end up in larger, more
    connected clusters. Each cluster accretes agents proportionally to the
    mean extraversion of its current members (rich-get-richer within clusters).

    Returns a mapping of cluster_id -> list[Agent].
    """
    n_clusters = max(2, math.ceil(len(agents) / agents_per_cluster))

    # Sort descending so high-extraversion agents anchor each cluster first.
    sorted_agents = sorted(agents, key=lambda a: a.profile.extraversion, reverse=True)

    clusters: dict[int, list[Agent]] = {i: [] for i in range(n_clusters)}

    for i in range(min(n_clusters, len(sorted_agents))):
        clusters[i].append(sorted_agents[i])

    for agent in sorted_agents[n_clusters:]:
        weights = [
            sum(m.profile.extraversion for m in members) / len(members) if members else 0.5
            for members in clusters.values()
        ]
        chosen = random.choices(list(clusters.keys()), weights=weights, k=1)[0]
        clusters[chosen].append(agent)

    return {cid: members for cid, members in clusters.items() if members}


# ── Graph Construction ─────────────────────────────────────────────────────────

def _cluster_hub(members: list[Agent]) -> Agent:
    """Return the highest-extraversion agent in a cluster — the hub."""
    return max(members, key=lambda a: a.profile.extraversion)


def _build_intra_cluster_edges(G: nx.Graph, members: list[Agent], p: float) -> None:
    """
    Wire a cluster's agents with Erdős–Rényi random edges.

    Delegates edge sampling to nx.erdos_renyi_graph, relabels its integer
    node indices to agent IDs, then merges the result into G.
    """
    node_ids = [a.id for a in members]
    er = nx.erdos_renyi_graph(len(node_ids), p)
    G.update(nx.relabel_nodes(er, dict(enumerate(node_ids))))


def _build_inter_cluster_edges(
    G: nx.Graph,
    clusters: dict[int, list[Agent]],
    m: int,
) -> None:
    """
    Connect cluster hubs with preferential attachment (Barabási–Albert style).

    Each hub preferentially attaches to already-connected hubs proportionally
    to their current degree, producing a scale-free inter-cluster topology.
    """
    hubs = [_cluster_hub(members) for members in clusters.values()]
    if len(hubs) < 2:
        return

    # Bootstrap with the first two hubs connected.
    connected = hubs[:2]
    G.add_edge(hubs[0].id, hubs[1].id)

    for hub in hubs[2:]:
        # G.degree[n] uses the DegreeView subscript — more idiomatic than G.degree(n).
        weights = [max(G.degree[h.id], 1) for h in connected]
        sampled = random.choices(connected, weights=weights, k=min(m, len(connected)))

        # dict.fromkeys preserves order while deduplicating by agent ID.
        for target in dict.fromkeys(t.id for t in sampled):
            if not G.has_edge(hub.id, target):
                G.add_edge(hub.id, target)

        connected.append(hub)


# ── Public API ─────────────────────────────────────────────────────────────────

@dataclass
class SocialNetwork:
    graph: nx.Graph
    clusters: dict[int, list[Agent]]  # cluster_id -> agents
    hubs: dict[int, Agent]            # cluster_id -> hub agent (story seed)
    agent_cluster: dict[int, int]     # agent_id -> cluster_id (O(1) lookup cache)

    def neighbours(self, agent_id: int) -> list[int]:
        """Return the IDs of all agents directly connected to agent_id."""
        return list(self.graph.neighbors(agent_id))

    def get_cluster_of(self, agent_id: int) -> int:
        """Return the cluster ID that agent_id belongs to."""
        return self.agent_cluster[agent_id]

    def cluster_subgraph(self, cluster_id: int) -> nx.Graph:
        """
        Return a read-only view of the subgraph induced by a single cluster.

        The returned SubGraph reflects any subsequent changes to the parent
        graph, consistent with how nx.Graph.subgraph behaves.
        """
        node_ids = [a.id for a in self.clusters[cluster_id]]
        return self.graph.subgraph(node_ids)

    def summary(self) -> str:
        G = self.graph
        n = G.number_of_nodes()
        avg_degree = sum(d for _, d in G.degree()) / n if n else 0.0
        hub_names = {cid: h.name for cid, h in self.hubs.items()}
        lines = [
            f"Nodes:          {n}",
            f"Edges:          {G.number_of_edges()}",
            f"Clusters:       {len(self.clusters)}",
            f"Density:        {nx.density(G):.4f}",
            f"Avg degree:     {avg_degree:.2f}",
            f"Avg clustering: {nx.average_clustering(G):.4f}",
            f"Connected:      {nx.is_connected(G)}",
            f"Components:     {nx.number_connected_components(G)}",
            f"Cluster hubs:   {hub_names}",
        ]
        return "\n".join(lines)


def build_network(agents: list[Agent], config: NetworkConfig | None = None) -> SocialNetwork:
    """
    Build the hybrid social network from a list of agents.

    Steps:
      1. Assign agents to clusters (extraversion-biased)
      2. Add dense intra-cluster edges (Erdős–Rényi)
      3. Connect cluster hubs with scale-free inter-cluster edges (BA)

    Returns a SocialNetwork with the graph, cluster map, and hub index.
    """
    config = config or NetworkConfig()

    clusters = assign_clusters(agents, config.agents_per_cluster)
    hubs = {cid: _cluster_hub(members) for cid, members in clusters.items()}
    agent_cluster = {
        agent.id: cid for cid, members in clusters.items() for agent in members
    }
    hub_ids = {h.id for h in hubs.values()}

    G = nx.Graph()
    G.add_nodes_from(
        (
            agent.id,
            {
                "name": agent.name,
                "extraversion": agent.profile.extraversion,
                "cluster_id": agent_cluster[agent.id],
                "is_hub": agent.id in hub_ids,
            },
        )
        for agent in agents
    )

    for members in clusters.values():
        _build_intra_cluster_edges(G, members, config.intra_cluster_p)

    _build_inter_cluster_edges(G, clusters, config.inter_cluster_m)

    return SocialNetwork(
        graph=G,
        clusters=clusters,
        hubs=hubs,
        agent_cluster=agent_cluster,
    )

