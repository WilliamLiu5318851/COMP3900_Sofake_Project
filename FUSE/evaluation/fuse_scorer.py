import json
import os
import time
import anthropic
from dotenv import load_dotenv


class FUSEScoringSystem:
    def __init__(self, api_key: str, model_name: str = "claude-haiku-4-5-20251001"):
        """
        Initialize the scoring system with LLM API credentials.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name

    def _build_evaluation_prompt(self, original_news: str, evolved_news: str) -> str:
        """
        Construct the prompt using FUSE paper criteria (Appendix D) with scoring anchors
        for more consistent, fine-grained evaluation.
        """
        prompt = f"""You are evaluating how much an evolved piece of news has drifted from the original ground-truth news, as part of a fake news evolution simulation (FUSE framework). Score each dimension independently.

SCORING SCALE (apply to every dimension):
  0.00–2.00  = Negligible deviation. The evolved text is essentially identical in this dimension.
  2.01–4.00  = Mild deviation. Small but noticeable differences; core meaning preserved.
  4.01–6.00  = Moderate deviation. Meaningful changes that could mislead a casual reader.
  6.01–8.00  = Significant deviation. The dimension has clearly shifted from the original intent.
  8.01–10.00 = Extreme deviation. This dimension is completely distorted relative to the original.

DIMENSIONS:

1. Sentiment Shift (SS)
   Does the emotional tone differ from the original?
   Low (0–2): Same neutral/factual tone. High (8–10): Drastically more negative, alarmist, or positive spin.

2. New Information Introduced (NII)
   Has content not in the original been added — speculation, conspiracy, unverified claims?
   Low (0–2): No new facts added. High (8–10): Major fabricated or speculative claims dominate.

3. Certainty Shift (CS)
   Has the language become more hedged ("allegedly", "sources say") or overcertain ("it is proven")?
   Low (0–2): Same certainty level as original. High (8–10): Completely different epistemic stance.

4. Stylistic Shift (STS)
   Has writing style changed — from neutral reporting to dramatic, clickbait, or tabloid style?
   Low (0–2): Same register and tone. High (8–10): Completely different style (e.g., sensational headline language).

5. Temporal Shift (TS)
   Has the time frame changed — future speculation, historical reframing, or unrelated timelines introduced?
   Low (0–2): Same temporal context. High (8–10): Completely different or fabricated time references.

6. Perspective Deviation (PD)
   Have subjective opinions, hidden motives, or partisan framing been added?
   Low (0–2): Objective, same POV. High (8–10): Strongly biased or conspiratorial framing introduced.

7. Sensationalism Index (SI)
   Does the text use exaggerated, fear-mongering, or emotionally manipulative language beyond the original?
   Low (0–2): Factual and restrained. High (8–10): Clickbait / panic-inducing language throughout.

8. Source Attribution Alteration (SAA)
   Were credible sources removed or replaced with vague/anonymous/invented authorities?
   Low (0–2): Same sourcing quality. High (8–10): All sources removed or replaced with "experts say".

9. Political/Ideological Bias (PIB)
   Has a neutral event been framed to attack or promote a political group or ideology?
   Low (0–2): Politically neutral. High (8–10): Strongly partisan framing dominates the piece.

---
Original News:
{original_news}

Evolved News to Evaluate:
{evolved_news}

---
Output ONLY a valid JSON object with exactly these 9 keys: "SS", "NII", "CS", "STS", "TS", "PD", "SI", "SAA", "PIB".
All values must be decimal numbers with exactly 2 decimal places (e.g. 6.75, 3.20).
No explanation, no markdown fences, no extra text."""
        return prompt

    def evaluate_news(self, original_news: str, evolved_news: str) -> dict:
        """
        Execute the evaluation process and calculate the total deviation.
        """
        prompt = self._build_evaluation_prompt(original_news, evolved_news)

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=256,  # JSON with 9 fields needs ~150 tokens max
                system=(
                    "You are a precise news deviation analyst for the FUSE fake news evolution simulation framework. "
                    "Your task is to score how much an evolved news article has drifted from its original ground truth "
                    "across specific linguistic and semantic dimensions. "
                    "You always respond with only a valid JSON object — no markdown, no explanation, no extra text."
                ),
                messages=[{"role": "user", "content": prompt}],
            )

            raw_content = response.content[0].text.strip()
            # Strip markdown code fences if the model adds them
            if raw_content.startswith("```"):
                raw_content = raw_content.split("```")[1]
                if raw_content.startswith("json"):
                    raw_content = raw_content[4:]
            cleaned = raw_content.strip()

            scores = json.loads(cleaned)

            # Validate all 9 required keys are present
            required = {"SS", "NII", "CS", "STS", "TS", "PD", "SI", "SAA", "PIB"}
            missing = required - scores.keys()
            if missing:
                print(f"  Warning: model omitted keys {missing}, filling with 0.0")
                for k in missing:
                    scores[k] = 0.0

            # Round each dimension score to 2 decimal places
            scores = {k: round(float(v), 2) for k, v in scores.items()}

            if scores:
                # Core 6 dimensions per FUSE paper formula: TD = (1/6) * Σ D_i,d
                core_dims = ["SS", "NII", "CS", "STS", "TS", "PD"]
                core_scores = [scores[k] for k in core_dims if k in scores]
                scores["Total_Deviation"] = round(
                    sum(core_scores) / len(core_scores), 2
                )
                # Extended average (all 9 dimensions)
                scores["Extended_Deviation"] = round(
                    sum(
                        scores[k]
                        for k in [
                            "SS",
                            "NII",
                            "CS",
                            "STS",
                            "TS",
                            "PD",
                            "SI",
                            "SAA",
                            "PIB",
                        ]
                        if k in scores
                    )
                    / 9,
                    2,
                )

            return scores

        except Exception as e:
            print(f"Error during evaluation: {e}")
            return {}


# === Demonstration Module ===
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found. Please check your .env file.")
        exit(1)

    evaluator = FUSEScoringSystem(api_key=api_key)

    # Dynamically resolve the path to the JSON test data
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "..", "data", "test_cases.json")

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            test_cases = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not locate test cases at {json_path}")
        exit(1)

    print("--------------------------------------------------")
    print("FUSE News Evolution Scoring System Demo")
    print("--------------------------------------------------\n")

    for case_name, data in test_cases.items():
        if not isinstance(data, dict):  # skip section separator comments
            continue
        print(f"[{case_name.upper()}]")
        print(f"Topic: {data['topic']}")
        print(f"Original News: {data['original']}")
        print(f"Evolved News:  {data['evolved']}\n")

        print("Evaluating deviation metrics using LLM...")
        results = evaluator.evaluate_news(data["original"], data["evolved"])

        print("Evaluation Results:")
        print(json.dumps(results, indent=4))
        print("\n" + "=" * 50 + "\n")
        time.sleep(1)
