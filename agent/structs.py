import os
import random
import json
import time
from dataclasses import asdict, dataclass, field
from urllib import response
from groq import Groq, RateLimitError


# [MODIFIED] 移除了原先放在这里的全局 client 初始化

def llm_call(prompt: str) -> str:
    # [NEW] 在函数内部初始化客户端，确保它能抓取到被 os.fork() 注入的全新 API Key
    raw_keys = os.getenv("GROQ_API_KEY", "")
    actual_key = raw_keys.split(",")[0].strip()  # 永远只拿第一把干净的钥匙
    
    client = Groq(api_key=actual_key)
    
    # [NEW] 加入自动重试机制，最多重试 3 次
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content # type: ignore
        except RateLimitError as e:
            if attempt < max_retries - 1:
                # 如果被限流了，打印一行提示，然后睡 3 秒再重试
                print(f"⚠️ [PID: {os.getpid()}] 触发 API 限流，等待 3 秒后重试 (第 {attempt + 1} 次)...")
                time.sleep(3)
            else:
                # 如果重试了 3 次还是不行，那只能报错了
                raise e
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
    engagement: int = 0


@dataclass
class Agent:
    id: int
    name: str
    profile: HEXACOProfile
    memory: list[str] = field(default_factory=list)
    seen_post_ids: set[str] = field(default_factory=set)


@dataclass
class AgentAction:
    agent_id: int
    action: str
    text: str | None
    source_post_id: str