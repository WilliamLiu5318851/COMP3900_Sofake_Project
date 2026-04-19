import json
from structs import Agent, llm_call
from prompts import describe_trait


# ── Prompt Construction ───────────────────────────────────────────────────────────────

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

def clean_llm_json(raw: str) -> str:
    import re
    text = raw.strip()
    text = text.replace("```json", "").replace("```","").strip()

    start = text.find("[")
    end = text.rfind("]")
    text = text[start:end+1].strip()

    # Fix missing commas between consecutive string elements
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)

    return text



def generate_initial_memory(agent: Agent, visible_context: str) -> list[str]:
    prompt = build_initial_memory_prompt(agent, visible_context)
    raw = llm_call(prompt)
    cleaned = clean_llm_json(raw)
                                                         
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse initial memory: {raw}")
    
    if not isinstance(data, list):
        raise ValueError("Initial memory should be a list of strings.")
    
    memory = []
    for item in data:
        text = str(item).strip()
        if text:
            memory.append(text)

    return memory

def initialise_agent_memory(agent: Agent, visible_context: str) -> None:
    agent.memory = generate_initial_memory(agent, visible_context)