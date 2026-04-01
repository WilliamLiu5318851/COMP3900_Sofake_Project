import os
import random
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="SoFake Agent Service")


class SimulateRequest(BaseModel):
    ground_truth: str
    agent_count: int = 30
    steps: int = 60
    seed: int = 42
    role_mix: dict = {"spreader": 35, "commentator": 35, "verifier": 15, "bystander": 15}


class SimulateResponse(BaseModel):
    posts: list[dict]
    summary: dict


@app.get("/")
def root():
    return {"message": "Agent service is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    from structs import Agent, HEXACOProfile, Post
    from prompts import agent_process_post, classify_post_signals, get_post_signals
    from network import build_network, NetworkConfig

    random.seed(req.seed)

    # --- 1. Create agents ---
    agents = [
        Agent(id=i, name=f"Agent_{i}", profile=HEXACOProfile.random())
        for i in range(req.agent_count)
    ]
    agent_map = {a.id: a for a in agents}

    # --- 2. Build network ---
    network = build_network(agents, NetworkConfig())

    # --- 3. Seed post (ground truth) ---
    seed_signals = classify_post_signals(
        post_text=req.ground_truth,
        generation=0,
        source_post_id="ground_truth",
    )
    seed_post = Post(
        id="ground_truth",
        author_id="system",
        text=req.ground_truth,
        signals=seed_signals,
        parent_id=None,
    )

    # --- 4. Initialise hub agents' feeds with the seed post ---
    # Each cluster hub is the first to see the ground truth
    post_store: dict[str, Post] = {"ground_truth": seed_post}
    # feed: agent_id -> list of post ids waiting to be processed
    feeds: dict[int, list[str]] = {a.id: [] for a in agents}
    for hub in network.hubs.values():
        feeds[hub.id].append("ground_truth")

    result_posts = []

    # --- 5. Simulation loop ---
    for step in range(req.steps):
        # Collect agents that have something in their feed this step
        active_agents = [a for a in agents if feeds[a.id]]
        if not active_agents:
            break

        new_posts_this_step: list[Post] = []

        for agent in active_agents:
            post_id = feeds[agent.id].pop(0)
            post = post_store[post_id]

            action_result = agent_process_post(agent, post, req.ground_truth)

            result_posts.append({
                "step": step,
                "agent_id": agent.id,
                "action": action_result.action,
                "text": action_result.text,
                "source_post_id": post_id,
                "generation": post.signals.generation,
            })

            # If the agent produced new content, create a new Post and
            # push it to this agent's neighbours
            if action_result.text:
                new_signals = get_post_signals(action_result.action, action_result.text, post)
                new_post_id = str(uuid.uuid4())
                new_post = Post(
                    id=new_post_id,
                    author_id=str(agent.id),
                    text=action_result.text,
                    signals=new_signals,
                    parent_id=post_id,
                )
                post_store[new_post_id] = new_post
                new_posts_this_step.append(new_post)

                for neighbour_id in network.neighbours(agent.id):
                    feeds[neighbour_id].append(new_post_id)

    # --- 6. Summary stats ---
    generations = [p["generation"] for p in result_posts if p["text"]]
    summary = {
        "total_steps_run": step + 1 if result_posts else 0,
        "total_posts_generated": len([p for p in result_posts if p["text"]]),
        "actions_breakdown": {},
        "max_generation": max(generations) if generations else 0,
    }
    for entry in result_posts:
        a = entry["action"]
        summary["actions_breakdown"][a] = summary["actions_breakdown"].get(a, 0) + 1

    return SimulateResponse(posts=result_posts, summary=summary)
