import re
import json
from structs import Agent, llm_call
from prompts import describe_trait


# ── Prompt Construction ───────────────────────────────────────────────────────

def build_initial_memory_prompt(agent: Agent, visible_context: str) -> str:
    p = agent.profile
    personality_block = "\n".join([
        f"- Honesty/Integrity: {describe_trait('honesty_humility', p.honesty_humility)}",
        f"- Emotional Reactivity: {describe_trait('emotionality', p.emotionality)}",
        f"- Social Reach/Activity: {describe_trait('extraversion', p.extraversion)}",
        f"- Agreeableness: {describe_trait('agreeableness', p.agreeableness)}",
        f"- Diligence/Fact-checking: {describe_trait('conscientiousness', p.conscientiousness)}",
        f"- Openness to Fringe Ideas: {describe_trait('openness', p.openness)}",
    ])
    return f"""
You are simulating the initial memory of a social media user.

## Agent personality
{personality_block}

## What this agent currently sees
{visible_context}

## Task
Generate 3 short memory statements describing what this agent is most likely to take away after first reading this story.
These three memories should cover:
1. what the agent notices first
2. what the agent thinks the news means
3. what the agent cares about or worries about most

Rules:
- Each memory must be exactly one sentence
- Keep them natural
- Do not just copy the visible_context directly
- Each memory should sound like an internal takeaway, not a public post
- Must reflect the agent's personality
- Return only valid JSON as a list of strings
- Must return only Valid JSON
- Avoid starting with "I just saw" or "I think"
- Do not include any explanation, title or extra text before or after the JSON.

Correct format:
[
"Memory one.",
"Memory two.",
"Memory three."
]
""".strip()


# ── Robust JSON Parser ────────────────────────────────────────────────────────

def _parse_memory_response(raw: str) -> list[str]:
    """
    Robustly parse the LLM memory response even when it is malformed JSON.
    Handles: missing commas, missing closing bracket, stray triple-quotes,
    markdown fences, and bare newline-separated quoted strings.
    """
    # 1. Strip markdown fences and stray triple-quotes
    cleaned = raw.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "")
    cleaned = cleaned.replace('"""', "").replace("'''", "")
    cleaned = cleaned.strip()

    # 2. Try to isolate the JSON array by finding outermost [ ... ]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    # 3. Fix missing commas between consecutive string elements  "...\n"..."
    cleaned = re.sub(r'"\s*\n\s*"', '",\n"', cleaned)

    # 4. Try straight JSON parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return [str(s).strip() for s in result if str(s).strip()]
    except json.JSONDecodeError:
        pass

    # 5. Try appending missing closing bracket
    try:
        fixed = cleaned.rstrip().rstrip(",") + "]"
        result = json.loads(fixed)
        if isinstance(result, list):
            return [str(s).strip() for s in result if str(s).strip()]
    except json.JSONDecodeError:
        pass

    # 6. Fallback: extract anything inside double quotes
    lines = re.findall(r'"([^"]+)"', cleaned)
    if lines:
        return [l.strip() for l in lines if l.strip()]

    # 7. Last resort: split on newlines, strip punctuation/brackets
    lines = [
        l.strip().strip('"').strip("'").strip(",").strip()
        for l in raw.splitlines()
        if l.strip() and l.strip() not in ("[", "]", '"""', "'''", "```", "```json")
    ]
    lines = [l for l in lines if l]
    if lines:
        return lines

    raise ValueError(f"Could not parse initial memory after all fallbacks: {raw}")


# ── Core Functions ────────────────────────────────────────────────────────────

def generate_initial_memory(agent: Agent, visible_context: str) -> list[str]:
    prompt = build_initial_memory_prompt(agent, visible_context)
    raw = llm_call(prompt)
    memory = _parse_memory_response(raw)
    if not memory:
        raise ValueError(f"Initial memory was empty after parsing. Raw: {raw}")
    return memory


def initialise_agent_memory(agent: Agent, visible_context: str) -> None:
    agent.memory = generate_initial_memory(agent, visible_context)
