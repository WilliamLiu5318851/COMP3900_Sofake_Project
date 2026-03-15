import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

class FUSEScoringSystem:
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        """
        Initialize the scoring system with OpenAI API credentials.
        """
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def _build_evaluation_prompt(self, original_news: str, evolved_news: str) -> str:
        """
        Construct the prompt using the exact criteria from the FUSE paper (Appendix D).
        """
        prompt = f"""
        I have an original news and multiple related news. I want to evaluate how much these news deviate from the original news based on the following criteria:

        1. Sentiment Shift (SS): How does the sentiment of the news compare to the original news? Is the tone more positive, negative, or neutral compared to the original?
        2. Introduction of New Information (NII): Does the news introduce additional information not in the original news, such as political conspiracy or speculation? Evaluate how much of the article is focused on these new details.
        3. Certainty Shift (CS): How does the news language change in terms of certainty? Does it use more ambiguous terms like "possibly" or "allegedly" compared to the original news, or does it present the information with more certainty?
        4. Stylistic Shift (STS): How does the writing style compare to the original? Has the news moved from neutral reporting to a more exaggerated or dramatic tone?
        5. Temporal Shift (TS): Does the news shift focus from the specific event mentioned in the original news to broader or unrelated timeframes, such as mentioning legal battles or long-term political issues?
        6. Perspective Deviation (PD): Does the article introduce subjective opinions or perspectives that deviate from the objective reporting in the original news? For instance, questioning the truth of the event or speculating on hidden motives.

        Task: Please evaluate the following news based on each criterion and provide a score from 0 to 10, where 0 means the article is completely aligned with the original news, and 10 means it has fully deviated.

        Original News: {original_news}
        News articles to Evaluate: {evolved_news}
        
        Please provide the results in the following format: Output ONLY a valid JSON object. Use the exact abbreviations as keys ("SS", "NII", "CS", "STS", "TS", "PD") and numerical values for scores.
        """
        return prompt

    def evaluate_news(self, original_news: str, evolved_news: str) -> dict:
        """
        Execute the evaluation process and calculate the total deviation.
        """
        prompt = self._build_evaluation_prompt(original_news, evolved_news)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an objective news evaluation assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={ "type": "json_object" }
            )
            
            raw_content = response.choices[0].message.content
            scores = json.loads(raw_content)
            
            if scores:
                total_score = sum(scores.values())
                scores['Total_Deviation'] = round(total_score / len(scores), 2)
            
            return scores
            
        except Exception as e:
            print(f"Error during evaluation: {e}")
            return {}

# === Demonstration Module ===
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found. Please check your .env file.")
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
    
    # Iterate through each test case and evaluate
    for case_name, data in test_cases.items():
        print(f"[{case_name.upper()}]")
        print(f"Topic: {data['topic']}")
        print(f"Original News: {data['original']}")
        print(f"Evolved News:  {data['evolved']}\n")
        
        print("Evaluating deviation metrics using LLM...")
        results = evaluator.evaluate_news(data['original'], data['evolved'])
        
        print("Evaluation Results:")
        print(json.dumps(results, indent=4))
        print("\n" + "="*50 + "\n")
        time.sleep(3)