from prompts import *
from initial_memory import initialise_agent_memory


# ── Trial Script ──────────────────────────────────────────────────────────────

def run_trial(i: int):
    ground_truth = """
Scientists at a major US university have published a study suggesting that 
microplastics found in common bottled water brands may be interfering with 
human hormone regulation. The study, which tracked 3,000 participants over 
5 years, found a statistically significant correlation between bottled water 
consumption and disrupted cortisol and thyroid levels. The lead researcher 
stated the findings are 'concerning but not yet conclusive'. Health authorities 
have not yet issued any official guidance in response to the study.
"""

    # Seed the ground truth as the first post
    seed_signals = classify_post_signals(
        post_text=ground_truth,
        generation=0,
        source_post_id="ground_truth"
    )

    seed_post = Post(
        id="ground_truth",
        author_id="system",
        text=ground_truth.strip(),
        signals=seed_signals,
        parent_id=None,
    )
    # Create one agent
    agent = Agent(
        id=i,
        name="Alex",
        profile=HEXACOProfile.random(),
    )
    initialise_agent_memory(agent, ground_truth)
    # Print agent profile
    print("=" * 60)
    print(f"Agent: {agent.name}")
    print(f"  Honesty-Humility:  {agent.profile.honesty_humility:.2f}")
    print(f"  Emotionality:      {agent.profile.emotionality:.2f}")
    print(f"  Extraversion:      {agent.profile.extraversion:.2f}")
    print(f"  Agreeableness:     {agent.profile.agreeableness:.2f}")
    print(f"  Conscientiousness: {agent.profile.conscientiousness:.2f}")
    print(f"  Openness:          {agent.profile.openness:.2f}")
    print("=" * 60)

    # Print seed post signals
    print("\nGround Truth Post:")
    print(f"  {seed_post.text}")
    print(f"\nPost Signals:")
    print(f"  emotional_charge: {seed_signals.emotional_charge:.2f}")
    print(f"  controversy:      {seed_signals.controversy:.2f}")
    print(f"  fringe_score:     {seed_signals.fringe_score:.2f}")
    print(f"  threat_level:     {seed_signals.threat_level:.2f}")
    print("=" * 60)

    print("\nInitial memory:")
    for m in agent.memory:
        print(f"  - {m}")
    print("=" * 60)

    # Run agent
    action_result = agent_process_post(agent, seed_post, ground_truth)
    print(f"\nAction taken: {action_result.action.upper()}")
    if action_result.text:
        print(f"\nAgent's post:\n  {action_result.text}")

        # Classify the new post's signals
        new_signals = get_post_signals(action_result.action, action_result.text, seed_post)
        print(f"\nNew Post Signals (generation {new_signals.generation}):")
        print(f"  emotional_charge: {new_signals.emotional_charge:.2f}  (was {seed_signals.emotional_charge:.2f})")
        print(f"  controversy:      {new_signals.controversy:.2f}  (was {seed_signals.controversy:.2f})")
        print(f"  fringe_score:     {new_signals.fringe_score:.2f}  (was {seed_signals.fringe_score:.2f})")
        print(f"  threat_level:     {new_signals.threat_level:.2f}  (was {seed_signals.threat_level:.2f})")
    else:
        print("  (no text generated for this action)")

    print("=" * 60)


if __name__ == "__main__":
    run_trial(1)
