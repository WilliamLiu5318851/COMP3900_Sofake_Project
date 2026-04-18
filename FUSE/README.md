# FUSE-EVAL: Fake News Deviation Scoring Service

A FastAPI microservice implementing the FUSE framework. It uses an LLM to evaluate how much an evolved news post deviates from an original/parent text across nine dimensions, returning per-dimension scores plus aggregated `Total_Deviation` and `Extended_Deviation`.

This service is consumed by the `backend` service in `docker-compose.yml` during the simulation pipeline — for each sampled evolved post, backend calls FUSE twice: once against the ground truth, once against the parent post.

## Scoring Dimensions

Each dimension is scored on a 0–10 scale (0 = negligible deviation, 10 = extreme deviation).

**Core 6 (used for `Total_Deviation`):**
- **SS** — Sentiment Shift: change in emotional tone
- **NII** — New Information Introduced: unverified details or speculation
- **CS** — Certainty Shift: change in epistemic confidence / hedging
- **STS** — Stylistic Shift: neutral vs. sensational writing register
- **TS** — Temporal Shift: modifications to time references
- **PD** — Perspective Deviation: subjective opinion added to objective reporting

**Extended 3 (added to `Total_Deviation` to compute `Extended_Deviation`):**
- **SI** — Sensationalism Index: fear-mongering / panic-inducing framing
- **SAA** — Source Attribution Alteration: credible sources removed or replaced
- **PIB** — Political/Ideological Bias: partisan framing added

Aggregations:
- `Total_Deviation = mean(SS, NII, CS, STS, TS, PD)`
- `Extended_Deviation = mean(all 9)`

## Project Structure

```text
FUSE/
├── Dockerfile
├── main.py                  # FastAPI app (endpoints)
├── requirements.txt
├── README.md
├── data/
│   └── test_cases.json      # Sample pairs for CLI/demo testing
└── evaluation/
    └── fuse_scorer.py       # Scoring logic + LLM API client
```

## API

Runs on port `8002` inside the Docker network; exposed as `9002` on the host.

| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | `/healthcheck`   | Liveness check + scorer ready state  |
| POST   | `/api/evaluate`  | Score one evolved post vs. original  |

### POST `/api/evaluate`

Request:
```json
{
  "original": "The original or parent news text.",
  "evolved":  "The evolved post to evaluate."
}
```

Response:
```json
{
  "SS": 7.5, "NII": 6.2, "CS": 5.8, "STS": 8.1, "TS": 0.5,
  "PD": 4.3, "SI": 8.4, "SAA": 3.2, "PIB": 1.1,
  "Total_Deviation": 5.4,
  "Extended_Deviation": 5.01
}
```

## Setup — Docker (recommended)

From the repository root:

1. Put your FUSE LLM API key in `.env` at the project root (the FUSE container picks it up via `docker-compose.yml`):
   ```
   ANTHROPIC_API_KEY=your_fuse_api_key_here
   ```
   **Important:** no space after `=`, no trailing whitespace. Use LF line endings (not CRLF) to avoid env-parsing issues.

2. Start the service (with the rest of the stack):
   ```bash
   docker-compose up -d fuse
   ```

3. Verify:
   ```bash
   curl http://localhost:9002/healthcheck
   # {"status":"healthy","scorer_ready":true}
   ```

4. Quick sanity test:
   ```bash
   curl -X POST http://localhost:9002/api/evaluate \
     -H "Content-Type: application/json" \
     -d '{"original":"Scientists found water is wet.","evolved":"BREAKING: Water causes wetness crisis!"}'
   ```

## Setup — Local (without Docker)

1. From the `FUSE/` directory:
   ```bash
   pip install -r requirements.txt
   ```

2. Set the API key in your environment:
   ```bash
   export ANTHROPIC_API_KEY=your_fuse_api_key_here   # macOS/Linux
   set ANTHROPIC_API_KEY=your_fuse_api_key_here      # Windows CMD
   $env:ANTHROPIC_API_KEY="your_fuse_api_key_here"   # Windows PowerShell
   ```

3. Run the service:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8002
   ```

4. (Optional) Run the CLI demo over the bundled test cases:
   ```bash
   python evaluation/fuse_scorer.py
   ```

## Notes

- Errors returned by the LLM provider (e.g., `401 invalid x-api-key`) surface as HTTP 500 from `/api/evaluate`. Check FUSE container logs for the underlying reason:
  ```bash
  docker-compose logs --tail=50 fuse
  ```
- The backend service (`backend/main.py`) silently skips posts for which FUSE returns a non-200 response, so a bad API key manifests on the frontend as empty `fuse_evaluations`. Always verify `/healthcheck` and a direct `/api/evaluate` call when debugging.
- `.env` must **not** be committed. It is listed in the root `.gitignore`.
