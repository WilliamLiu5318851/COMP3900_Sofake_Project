from __future__ import annotations
import random
import json
from dataclasses import asdict, dataclass, field
from urllib import response
from groq import Groq


import os
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def llm_call(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class HEXACOProfile:
    honesty_humility: float
    emotionality: float
    extraversion: float
    agreeableness: float
    conscientiousness: float
    openness: float

    @classmethod
    def random(cls):
        """
        Generates a new HEXACOProfile with six random float values between 0 and 1.

        Returns:
            An instance of the class initialized with six random float values.
        """
        return cls(*[random.random() for _ in range(6)])

    @classmethod
    def bad_actor(cls):
        
        return cls(
            honesty_humility=random.uniform(0.0, 0.2),
            emotionality=random.uniform(0.3, 0.6),
            extraversion=random.uniform(0.7, 1.0),
            agreeableness=random.uniform(0.0, 0.3),
            conscientiousness=random.uniform(0.3, 0.6),
            openness=random.uniform(0.5, 0.9),
        )


@dataclass
class PostSignals:
    emotional_charge: float
    controversy: float
    fringe_score: float
    threat_level: float
    source_post_id: str
    generation: int


@dataclass
class Post:
    id: str
    author_id: str
    text: str
    signals: PostSignals
    parent_id: str | None = None


@dataclass
class Agent:
    id: int
    name: str
    profile: HEXACOProfile
    memory: list[str] = field(default_factory=list)


@dataclass
class AgentAction:
    agent_id: str
    action: str
    text: str | None
    source_post_id: str