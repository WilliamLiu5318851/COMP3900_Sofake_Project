from structs import Agent, HEXACOProfile, PostSignals
from network import build_network, NetworkConfig, elect_hubs, cosine_similarity
from prompts import compute_action_probabilities, describe_trait


def test_hexaco_bad_actor_profile():
    """Verify the bad_actor factory generates expected trait ranges."""
    profile = HEXACOProfile.bad_actor()
    assert 0.0 <= profile.honesty_humility <= 0.2
    assert 0.3 <= profile.emotionality <= 0.6
    assert 0.7 <= profile.extraversion <= 1.0
    assert 0.0 <= profile.agreeableness <= 0.3
    assert 0.3 <= profile.conscientiousness <= 0.6
    assert 0.5 <= profile.openness <= 0.9


# --- 1. HEXACO Distribution Tests ---


def test_hexaco_distribution_range():
    """Verify that HEXACO random values are within the [0.0, 1.0] range."""
    profile = HEXACOProfile.random()
    traits = [
        profile.honesty_humility,
        profile.emotionality,
        profile.extraversion,
        profile.agreeableness,
        profile.conscientiousness,
        profile.openness,
    ]
    for val in traits:
        assert 0.0 <= val <= 1.0


def test_hexaco_random_produces_variety():
    """Two random profiles should not be identical (with overwhelming probability)."""
    p1 = HEXACOProfile.random()
    p2 = HEXACOProfile.random()
    traits1 = (
        p1.honesty_humility,
        p1.emotionality,
        p1.extraversion,
        p1.agreeableness,
        p1.conscientiousness,
        p1.openness,
    )
    traits2 = (
        p2.honesty_humility,
        p2.emotionality,
        p2.extraversion,
        p2.agreeableness,
        p2.conscientiousness,
        p2.openness,
    )
    assert traits1 != traits2


# --- 2. Interaction Logic Tests ---


def test_action_probability_normalization():
    """Verify the calculation logic for action probabilities."""
    profile = HEXACOProfile.random()
    signals = PostSignals(0.5, 0.5, 0.5, 0.5, "source_1", 1)

    probs = compute_action_probabilities(profile, signals)

    # Ensure key behaviour probabilities exist and are non-negative
    assert "like" in probs
    assert "retweet" in probs
    assert probs["like"] >= 0

    # Total engagement (excluding 'ignore') should not exceed 1.0
    total_engagement = sum(v for k, v in probs.items() if k != "ignore")
    assert total_engagement <= 1.0


def test_trait_description_mapping():
    """Verify that trait scores are accurately mapped to text descriptions."""
    high_desc = describe_trait("honesty_humility", 1.0)
    assert "strict standard of accuracy" in high_desc

    low_desc = describe_trait("honesty_humility", 0.1)
    assert "deliberately distort" in low_desc


# --- 3. Network Topology & Node Generation Tests ---


def test_network_node_creation():
    """Verify that the network generates the correct number of nodes and clusters."""
    agents = [
        Agent(id=i, name=f"Agent_{i}", profile=HEXACOProfile.random())
        for i in range(20)
    ]
    config = NetworkConfig(agents_per_cluster=10)

    social_net = build_network(agents, config)

    assert social_net.graph.number_of_nodes() == 20
    # 20 agents at 10 per cluster → 2 clusters
    assert len(social_net.clusters) == 2


def test_elect_hubs_logic():
    """Verify that the agents with the highest extraversion are selected as Hubs."""
    a1 = Agent(1, "Quiet", HEXACOProfile(0.5, 0.5, 0.1, 0.5, 0.5, 0.5))
    a2 = Agent(2, "Loud", HEXACOProfile(0.5, 0.5, 0.9, 0.5, 0.5, 0.5))
    a3 = Agent(3, "Medium", HEXACOProfile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5))

    # With 3 agents and 2 per cluster, it should elect max(2, ceil(3/2))=2 hubs
    hubs = elect_hubs([a1, a2, a3], agents_per_cluster=2)

    assert len(hubs) == 2
    assert hubs[0].id == 2  # 0.9 extraversion
    assert hubs[1].id == 3  # 0.5 extraversion


def test_cosine_similarity():
    """Verify cosine similarity calculation between agents."""
    a1 = Agent(1, "A1", HEXACOProfile(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    a2 = Agent(2, "A2", HEXACOProfile(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    a3 = Agent(3, "A3", HEXACOProfile(0.0, 1.0, 0.0, 0.0, 0.0, 0.0))

    assert cosine_similarity(a1, a2) == 1.0
    assert cosine_similarity(a1, a3) == 0.0


def test_network_has_edges():
    """A network with enough agents should have at least some edges."""
    agents = [
        Agent(id=i, name=f"Agent_{i}", profile=HEXACOProfile.random())
        for i in range(10)
    ]
    social_net = build_network(agents, NetworkConfig())
    assert social_net.graph.number_of_edges() > 0
