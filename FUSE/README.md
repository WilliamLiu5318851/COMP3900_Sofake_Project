# FUSE-EVAL: Fake News Deviation Scoring System

This module is developed for the COMP3900 Sprint 1 Progressive Demo A. It implements a quantifiable evaluation system based on the FUSE framework to measure how much evolved news deviates from the original true news. 

## Core Features

The system utilizes an LLM (GPT-4o-mini) to evaluate textual deviation across 6 specific dimensions, generating a quantifiable `Total_Deviation` score:
- **SS (Sentiment Shift)**: Changes in emotional tone.
- **NII (New Information Introduced)**: Addition of unverified details or speculations.
- **CS (Certainty Shift)**: Variations in the level of confidence.
- **STS (Stylistic Shift)**: Alterations in writing style or dramatic tone.
- **TS (Temporal Shift)**: Modifications to time references.
- **PD (Perspective Deviation)**: Introduction of subjective opinions into objective reporting.

## Project Structure

```text
fake_news_project/
├── .env                  # Environment variables (DO NOT COMMIT)
├── .gitignore            # Files to be ignored by Git
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies
├── data/
│   └── test_cases.json   # Sample original and evolved news for testing
└── evaluation/
    └── fuse_scorer.py    # Core scoring system and API integration

## Setup Instructions
1. Clone the repository and navigate to the project directory
Ensure you are in the root directory fake_news_project/ before proceeding.

2. Install dependencies
Install the required Python packages using pip:

Bash
pip install -r requirements.txt
3. Configure Environment Variables
Create a .env file in the root directory. Add your OpenAI API key to this file:

Plaintext
OPENAI_API_KEY=your_actual_api_key_here
Note: Ensure .env is listed in your .gitignore file to prevent leaking credentials.

Usage
To run the scoring system demonstration in your terminal, execute the following command:

Bash
python evaluation/fuse_scorer.py
The script will process the predefined test cases, connect to the OpenAI API, and output a JSON object containing the scores for all 6 dimensions along with the calculated Total Deviation.