"""
feed.py — Feed construction and ranking for the newsreel simulation.

Design:
  - Visibility:  posts from direct neighbours + neighbours-of-neighbours (2 hops)
  - Ranking:     mixed score = 0.5 * signal_score + 0.5 * recency_score
  - Personalisation: agent's openness and emotionality bias which posts are
                     surfaced (high openness boosts fringe posts; high
                     emotionality boosts emotionally charged / threatening posts)
  - Feed cap:    top FEED_SIZE posts are returned; agent responds to all of them
                 (caller is responsible for LLM budget awareness)
"""

from dataclasses import dataclass, field
from structs import Agent, Post
from network import SocialNetwork

# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_FEED_SIZE = 3  # Posts surfaced to each agent per step
RECENCY_WEIGHT = 0.5  # Weight given to recency in mixed score
SIGNAL_WEIGHT = 0.5  # Weight given to signal strength in mixed score
ENGAGEMENT_BOOST = 0.2  # Additional weight for post engagement (likes/comments)

# ── Post Registry ──────────────────────────────────────────────────────────────


@dataclass
class PostRegistry:
    """
    Central store of all posts produced during the simulation.

    Posts are stored in insertion order so we can derive recency rank cheaply.
    """

    _posts: list[Post] = field(default_factory=list)
    _by_author: dict[int, list[Post]] = field(default_factory=dict)  # agent_id -> posts

    def add(self, post: Post, author_id: int) -> None:
        self._posts.append(post)
        self._by_author.setdefault(author_id, []).append(post)

    def posts_by(self, author_id: int) -> list[Post]:
        return self._by_author.get(author_id, [])

    def all_posts(self) -> list[Post]:
        return list(self._posts)

    def recency_rank(self, post: Post) -> int:
        """
        Returns 0-based insertion index. Higher = more recent.
        Used to normalise recency scores across the visible set.
        """
        try:
            return self._posts.index(post)
        except ValueError:
            return 0


# ── Visibility ─────────────────────────────────────────────────────────────────


def get_visible_posts(
    agent: Agent,
    network: SocialNetwork,
    registry: PostRegistry,
) -> list[Post]:
    """
    Collect all posts visible to an agent: direct neighbours + 2-hop neighbours.
    Excludes the agent's own posts and posts it has seen.
    """
    g = network.graph
    agent_id = agent.id

    one_hop = set(g.successors(agent_id))
    two_hop = set()
    for n in one_hop:
        two_hop.update(g.successors(n))

    visible_authors = (one_hop | two_hop) - {agent_id}

    posts: list[Post] = []
    for author_id in visible_authors:
        posts.extend(registry.posts_by(author_id))

    posts = [post for post in posts if post.id not in agent.seen_post_ids]

    return posts


# ── Scoring ────────────────────────────────────────────────────────────────────


def signal_score(post: Post) -> float:
    """
    Raw signal strength of a post — equal blend of all four signal dimensions.
    """
    s = post.signals
    return (s.emotional_charge + s.controversy + s.fringe_score + s.threat_level) / 4.0


def personalise_score(base_score: float, post: Post, agent: Agent) -> float:
    """
    Adjust a post's base signal score by the agent's HEXACO profile.

    - High openness  → fringe posts are boosted
    - High emotionality → emotionally charged and threatening posts are boosted

    Both adjustments are additive and capped so the final score stays in [0, 1].
    """
    s = post.signals
    p = agent.profile

    fringe_boost = p.openness * s.fringe_score * 0.3
    emotional_boost = p.emotionality * s.emotional_charge * 0.2
    threat_boost = p.emotionality * s.threat_level * 0.1

    return min(base_score + fringe_boost + emotional_boost + threat_boost, 1.0)


def mixed_score(
    post: Post,
    agent: Agent,
    recency_index: int,
    max_recency_index: int,
) -> float:
    """
    Final ranking score combining personalised signal strength and recency.

    recency_score = normalised insertion position (0 = oldest, 1 = most recent)
    signal_score  = personalised signal strength in [0, 1]
    mixed         = 0.5 * signal + 0.5 * recency
    """
    recency_score = (
        (recency_index / max_recency_index) if max_recency_index > 0 else 0.0
    )
    sig = personalise_score(signal_score(post), post, agent)
    return (
        SIGNAL_WEIGHT * sig
        + RECENCY_WEIGHT * recency_score
        + ENGAGEMENT_BOOST * post.engagement / 10.0
    )  # small boost for engagement


# ── Feed Builder ───────────────────────────────────────────────────────────────


def build_feed(
    agent: Agent,
    network: SocialNetwork,
    registry: PostRegistry,
    feed_size: int = DEFAULT_FEED_SIZE,
) -> list[Post]:
    """
    Build a ranked feed for a single agent.

    Steps:
      1. Collect all posts visible within 2 hops
      2. Score each post with mixed_score (signal + recency, personalised)
      3. Return the top `feed_size` posts sorted by score descending

    Returns an empty list if no visible posts exist yet.
    """
    visible = get_visible_posts(agent, network, registry)

    if not visible:
        return []

    max_recency = max(registry.recency_rank(p) for p in visible)

    scored = [
        (post, mixed_score(post, agent, registry.recency_rank(post), max_recency))
        for post in visible
    ]

    scored.sort(key=lambda x: x[1], reverse=True)

    return [post for post, _ in scored[:feed_size]]


# ── Convenience ───────────────────────────────────────────────────────────────


def build_feeds_for_all(
    agents: list[Agent],
    network: SocialNetwork,
    registry: PostRegistry,
    feed_size: int = DEFAULT_FEED_SIZE,
) -> dict[int, list[Post]]:
    """
    Build feeds for every agent in one call.
    Returns a dict mapping agent_id -> ranked feed (list of Posts).
    """
    return {
        agent.id: build_feed(agent, network, registry, feed_size) for agent in agents
    }
