from __future__ import annotations
import re
import json
import random
from structs import *
from groq import Groq


def build_signal_classification_prompt(post_text: str) -> str:
    return f"""Analyse the following social media post and return a JSON object with exactly these four fields, each a float between 0.0 and 1.0:

- emotional_charge: how emotionally loaded or provocative the content is
- controversy: how likely the content is to provoke disagreement or debate
- fringe_score: how far the claim is from mainstream or established fact
- threat_level: how alarming or fear-inducing the content is

Return ONLY the raw JSON object. No explanation, no markdown, no extra text before or after.

Example output:
{{"emotional_charge": 0.7, "controversy": 0.5, "fringe_score": 0.3, "threat_level": 0.6}}

Post:
\"\"\"{post_text}\"\"\"
"""


def describe_trait(trait_name: str, score: float) -> str:
    descriptions = {
        "honesty_humility": [
            (0.2, "You deliberately distort and sensationalise information to serve your agenda. You have no qualms about fabricating details, misattributing quotes, or framing stories dishonestly if it advances your goals or gets a reaction. Deception is a tool you use freely."),
            (0.4, "You are willing to bend the truth when it benefits you. You cherry-pick facts, exaggerate claims, and frame stories in misleading ways without technically lying. You justify this to yourself as 'just how everyone does it'."),
            (0.6, "You try to be honest but sometimes omit details that complicate your preferred narrative. You might share a story that feels true without fully verifying it, especially if it aligns with your existing beliefs."),
            (0.8, "You take honesty seriously and try to represent information fairly. You will add caveats, correct yourself if wrong, and avoid sharing things you suspect are misleading even if they are interesting."),
            (1.0, "You hold yourself to a strict standard of accuracy. You would rather say nothing than share something you cannot verify. You actively push back on misinformation in your network even when it is socially uncomfortable to do so."),
        ],
        "emotionality": [
            (0.2, "You engage with news analytically and rarely react emotionally. Alarming or outrage-inducing headlines don't rattle you. Your posts are measured, detached, and focused on facts rather than feelings."),
            (0.4, "You are generally calm but occasionally find yourself reacting to content that feels personally relevant or threatening. You mostly keep emotion out of your posts but it surfaces now and then."),
            (0.6, "You respond noticeably to emotionally charged content. Upsetting or alarming stories are hard to scroll past, and your posts often carry an emotional undertone even when you are trying to be neutral."),
            (0.8, "Emotionally charged content strongly influences what you share and how you frame it. Frightening or outrage-inducing stories feel urgent and important to you. Your posts often reflect anxiety, anger, or alarm."),
            (1.0, "You are highly anxious and emotionally reactive. Fear-based or threatening narratives feel viscerally real and demand an immediate response. Your posts are emotionally intense and you struggle to engage with upsetting content dispassionately."),
        ],
        "conscientiousness": [
            (0.2, "You share content the moment it catches your attention without pausing to question its source, accuracy, or context. Fact-checking feels unnecessary and slow. If it seems believable and interesting, you post it."),
            (0.4, "You occasionally glance at the source of something before sharing but usually trust your gut. If a story fits your understanding of the world you will share it without digging deeper."),
            (0.6, "You try to verify claims before sharing when you have time, but you don't always follow through. You are aware of misinformation but don't treat fact-checking as a hard rule."),
            (0.8, "You are diligent about checking sources before sharing. You look for corroboration, notice when something feels off, and will hold back a story until you are reasonably confident it is accurate."),
            (1.0, "You rigorously verify everything before sharing. You cross-reference sources, check publication dates, look for original reporting, and will refuse to share something even if it is widely circulated if you cannot confirm it yourself."),
        ],
        "extraversion": [
            (0.2, "You rarely post and when you do your audience is small. You consume far more than you produce. Your posts are infrequent, brief, and not written with a broad audience in mind."),
            (0.4, "You post occasionally and have a modest network. You don't seek attention but will share something if it feels worth saying. Your reach is limited and you are comfortable with that."),
            (0.6, "You are a reasonably active poster with a decent following. You engage with others regularly and enjoy being part of the conversation, though you don't dominate it."),
            (0.8, "You are highly active on social media and have a broad network. You post frequently, engage loudly, and enjoy being a visible voice in your community. People notice when you share something."),
            (1.0, "You are an extremely active and vocal presence with a large reach. You post constantly, engage with everyone, and treat social media as a primary channel for influence. Your shares carry significant amplification weight."),
        ],
        "agreeableness": [
            (0.2, "You are instinctively contrarian. You push back on prevailing narratives, challenge consensus, and enjoy poking holes in stories everyone else seems to accept. You are not hostile but you are not here to agree."),
            (0.4, "You are independently minded and somewhat skeptical of whatever the crowd believes. You will go along with a narrative if it holds up to your scrutiny but you are quick to voice doubts."),
            (0.6, "You generally get along with your network and tend to share content that fits the tone of your community. You will occasionally disagree but avoid prolonged conflict."),
            (0.8, "You are cooperative and conflict-averse. You amplify content that resonates with your network and rarely challenge the narratives circulating in your social circle even if you have private doubts."),
            (1.0, "You are highly conflict-averse and deeply influenced by social consensus. If everyone in your network believes something you find it very hard to resist sharing it too. Disagreeing feels socially risky and uncomfortable."),
        ],
        "openness": [
            (0.2, "You are deeply skeptical of unconventional narratives and fringe theories. You default to mainstream, established sources and treat alternative explanations with suspicion. Extraordinary claims require extraordinary evidence in your view."),
            (0.4, "You are cautious about fringe ideas but not completely closed to them. You will consider an alternative narrative if it comes from a credible source but you don't go looking for them."),
            (0.6, "You are open to a range of perspectives and enjoy content that challenges conventional thinking. You don't automatically distrust alternative viewpoints and will share them if they seem plausible."),
            (0.8, "You are drawn to unconventional ideas and find mainstream narratives overly simplistic. You actively seek out alternative perspectives and are willing to share fringe theories if they resonate with you."),
            (1.0, "You are highly receptive to fringe theories, alternative narratives, and heterodox ideas. Mainstream explanations often feel incomplete or manipulated to you. You enthusiastically share unconventional content and are a vector for fringe ideas spreading through your network."),
        ],
    }

    levels = descriptions[trait_name]
    for threshold, text in levels:
        if score <= threshold:
            return text
    return levels[-1][1]


# ── Signal Classification ─────────────────────────────────────────────────────

def classify_post_signals(post_text: str, generation: int, source_post_id: str) -> PostSignals:
    prompt = build_signal_classification_prompt(post_text)
    raw = llm_call(prompt)

    # Extract just the first {...} block — handles trailing text and markdown fences
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in LLM response: {raw}")

    data = json.loads(match.group())

    return PostSignals(
        emotional_charge=data["emotional_charge"],
        controversy=data["controversy"],
        fringe_score=data["fringe_score"],
        threat_level=data["threat_level"],
        source_post_id=source_post_id,
        generation=generation,
    )


def get_post_signals(action: str, new_text: str | None, parent_post: Post) -> PostSignals:
    if action in ("like", "retweet", "ignore", "report") or new_text is None:
        return parent_post.signals
    return classify_post_signals(
        new_text,
        generation=parent_post.signals.generation + 1,
        source_post_id=parent_post.id,
    )


def build_system_prompt(agent: Agent, ground_truth: str, action: str) -> str:
    p = agent.profile

    personality_block = "\n".join([
        f"- Honesty/Integrity: {describe_trait('honesty_humility', p.honesty_humility)}",
        f"- Emotional Reactivity: {describe_trait('emotionality', p.emotionality)}",
        f"- Social Reach/Activity: {describe_trait('extraversion', p.extraversion)}",
        f"- Agreeableness: {describe_trait('agreeableness', p.agreeableness)}",
        f"- Diligence/Fact-checking: {describe_trait('conscientiousness', p.conscientiousness)}",
        f"- Openness to Fringe Ideas: {describe_trait('openness', p.openness)}",
    ])

    action_instructions = {
        "quote_tweet": "Write a quote tweet — repost the content with your own commentary added. Keep it under 80 words.",
        "comment":     "Write a reply comment to this post. Keep it under 60 words.",
        "new_post":    "Write a completely new post retelling this story in your own words, as if you are sharing it fresh with your own followers. Keep it under 100 words.",
    }

    return f"""You are {agent.name}, a social media user in a news ecosystem simulation.

## Your Personality
{personality_block}

## The Original Ground Truth Story
{ground_truth}

## Your Recent Posts
{chr(10).join(agent.memory[-5:]) if agent.memory else "You have not posted yet."}

## Your Task
{action_instructions[action]}

Rules:
- Stay in character at all times
- Do NOT reference your personality traits explicitly
- Let your distortions or accuracy emerge naturally from your character
- Output only your post text, nothing else
"""


# ── Response Generation ───────────────────────────────────────────────────────

def generate_response(agent: Agent, post: Post, action: str, ground_truth: str) -> str:
    system = build_system_prompt(agent, ground_truth, action)
    prompt = f"You just saw this post:\n\n{post.text}"

    output = llm_call(system + "\n\n" + prompt)
    agent.memory.append(f"You posted: {output}")
    return output


def agent_process_post(agent: Agent, post: Post, ground_truth: str) -> AgentAction:
    agent.seen_post_ids.add(post.id)
    probs = compute_action_probabilities(agent.profile, post.signals)
    action = sample_action(probs)
    if action not in ("report", "ignore"):
        post.engagement += 1
        
    text = None
    if action in ("quote_tweet", "comment", "new_post"):
        text = generate_response(agent, post, action, ground_truth)

    return AgentAction(
        agent_id=agent.id,
        action=action,
        text=text,
        source_post_id=post.id,
    )


def compute_action_probabilities(profile: HEXACOProfile, signals: PostSignals) -> dict[str, float]:
    p_engage = profile.extraversion
    p_engage += profile.emotionality * signals.emotional_charge * 0.3
    p_engage += profile.openness * signals.fringe_score * 0.2
    p_engage = min(p_engage, 1.0)
    p_ignore = 1.0 - p_engage

    w_like      = profile.agreeableness * 0.6 + signals.emotional_charge * 0.2
    w_retweet   = (profile.agreeableness * 0.5 +
                   profile.extraversion * 0.3 +
                   (1 - profile.conscientiousness) * 0.2)
    w_quote     = (profile.extraversion * 0.4 +
                   (1 - profile.agreeableness) * 0.3 +
                   signals.controversy * 0.3)
    w_comment   = (profile.emotionality * signals.emotional_charge * 0.4 +
                   (1 - profile.agreeableness) * signals.controversy * 0.3 +
                   profile.extraversion * 0.2)
    w_new_post  = (profile.openness * signals.fringe_score * 0.3 +
                   profile.extraversion * 0.3 +
                   (1 - profile.conscientiousness) * 0.2 +
                   profile.emotionality * signals.threat_level * 0.2)
    w_report    = (signals.fringe_score * (1 - profile.honesty_humility) * 0.4 +
                   profile.conscientiousness * signals.fringe_score * 0.4 +
                   profile.emotionality * signals.threat_level * 0.2)

    weights = {
        "like":        w_like,
        "retweet":     w_retweet,
        "quote_tweet": w_quote,
        "comment":     w_comment,
        "new_post":    w_new_post,
        "report":      w_report,
    }

    total = sum(weights.values())
    normalised = {k: (v / total) * p_engage for k, v in weights.items()}
    normalised["ignore"] = p_ignore / 5
    print(f"Computed action probabilities: {normalised}")
    return normalised


def sample_action(probabilities: dict[str, float]) -> str:
    actions = list(probabilities.keys())
    weights = list(probabilities.values())
    return random.choices(actions, weights=weights, k=1)[0]