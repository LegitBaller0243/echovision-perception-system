# KLR.ai (Refactor of a Hackathon Prototype)

## Attribution
This codebase was originally cloned from a hackathon project:
- Original repository: `git@github.com:rayyansur/KLR.ai.git`
- My role: post-hackathon engineer focused on refactoring architecture, improving maintainability, and preparing the system for latency optimization.

I did not build the initial prototype from scratch; I inherited it and re-structured it for production-style development.

## Project Summary
KLR.ai is an assistive-vision system that:
1. Captures a camera frame from a web app.
2. Detects objects with YOLO.
3. Estimates scene depth (MiDaS/TFLite path with fallback).
4. Computes collision risk scoring.
5. Generates natural-language guidance via Azure OpenAI.
6. Triggers text-to-speech output.

Primary user scenario: spatial awareness support for visually impaired users.

## Interview Context: What Changed
The original hackathon layout mixed API routing, model inference, and integration logic in tightly coupled modules.  
I refactored it into clear layers:

```text
apps/
  api/          # HTTP interface only
  frontend/     # React UI
services/
  app_core/     # use-case orchestration
  perception/   # detection + depth + collision pipeline
integrations/
  llm/          # Azure OpenAI adapters
  audio/        # ElevenLabs STT/TTS adapters
tools/
  training/     # offline model training scripts
  inference/    # standalone inference scripts
```

## Current Architecture

### 1) Application Layer (`services/app_core`)
- Owns use-cases (`process_query`, `process_auto_detect`).
- Calls perception pipeline and LLM responders.
- Keeps business flow separate from model implementation details.

### 2) Perception Layer (`services/perception`)
- Modular pipeline runner with explicit stages:
  - `detect_objects` (YOLO)
  - `estimate_spatial` (depth + collision analysis)
- Model inference adapters are isolated under:
  - `inference/yolo/adapter.py`
  - `inference/midas/adapter.py`
- Collision reasoning isolated under `rules/collision_scoring.py`.

### 3) Integration Layer (`integrations`)
- Azure OpenAI prompt/response logic.
- ElevenLabs STT/TTS wrappers.
- External SDK concerns are separated from core logic.

### 4) API Layer (`apps/api`)
- Flask routes for `/health`, `/query`, `/auto-detect`, `/text-to-speech`.
- Handles request validation and image decoding only.
- Delegates business logic to `services/app_core`.

### 5) Frontend (`apps/frontend`)
- React/Vite app for camera capture and user interaction.
- Calls backend endpoints and shows health status.

## End-to-End Request Flow
1. Browser captures frame (`apps/frontend`).
2. Sends base64 image to `/auto-detect`.
3. API route decodes image to temp file.
4. `app_core` use-case runs perception pipeline:
   - YOLO object detection
   - depth estimation
   - collision risk analysis
5. Result context is sent to Azure OpenAI for response generation.
6. Final text is returned (and optionally passed to TTS route).

## Technical Challenges From the Inherited Hackathon Code
1. Tight coupling between routing, orchestration, inference, and vendor SDK code.
2. Ad-hoc import path hacks and inconsistent module boundaries.
3. Mixed concerns in single files (I/O + ML + orchestration + formatting).
4. Inconsistent API response shapes across endpoints.
5. Latency pressure from synchronous pipeline stages in one request path.
6. Limited test scaffolding and minimal operational observability.

## Refactor Results So Far
1. Clear separation of concerns (API vs app logic vs perception vs integrations).
2. Modular pipeline stages, easier to test and replace independently.
3. Isolated model adapters enabling future model swaps and benchmarking.
4. Cleaner folder structure for onboarding and interview readability.
5. Backward-compatible backend entry shims retained during migration.

## Latency Optimization Plan (Next Phase)
Planned improvements after architecture cleanup:
1. Warm model loading and singleton lifecycle controls.
2. Remove duplicated computation and avoid unnecessary image transcoding.
3. Optional async queue/worker mode for heavy inference stages.
4. Stage-level timing instrumentation and tracing.
5. Batch/parallel opportunities between independent operations where valid.
6. Prompt token reduction and response constraints for faster LLM round trips.

## Local Run Guide (Current)

### Backend
1. Install Python deps (root + backend/integration deps as needed).
2. Set env vars:
   - `AZURE_OPENAI_API_KEY`
   - `MODEL_DEPLOYMENT_NAME`
   - `ELEVENLABS_API_KEY`
   - Optional prompt filtering:
     - `LLM_MIN_CONFIDENCE` (default `0.45`)
     - `LLM_MAX_OBJECTS` (default `4`)
3. Run:
   - `python backend/app.py` (compat entrypoint)
   - or `python apps/api/src/main.py`

### Frontend
1. `cd apps/frontend`
2. `npm install`
3. `npm run dev`

Frontend expects backend at `http://127.0.0.1:5000`.

## LLM Model Comparison (Side-by-Side)
Use the compare script to test multiple models on the exact same prompt payload.

1. Set provider keys in `.env` as needed:
   - `AZURE_FOUNDRY_OPENAI_BASE_URL` (example: `https://<resource>.services.ai.azure.com/openai/v1/`)
   - `AZURE_FOUNDRY_API_KEY`
   - `AZURE_DEPLOYMENT_GPT_4O_MINI`
2. Edit:
   - `tools/llm_compare_models.example.json` (default single-model config for GPT-4o-mini)
   - `tools/llm_compare_case.example.json` (your query + detections + depth)
3. Run:
   - `python tools/llm_compare.py --runs-per-model 3 --concurrency 6 --output-json /tmp/llm_compare_report.json`

The script prints latency/token summaries and a sample response for each model, then sorts by average latency.
To compare additional models later, add them as extra entries in `tools/llm_compare_models.example.json`.

### Varied Cases + Perception Pipeline Cases
You can benchmark multiple cases in one run (including cases that call YOLO + MiDaS from an image).

1. Edit `tools/llm_compare_cases.example.json`
   - Inline case mode: provide `detections`, `depth_data`, `is_auto_detect`, optional `query`
   - Pipeline case mode: provide `image_path`, `is_auto_detect`, optional `query`
2. Run:
   - `python tools/llm_compare.py --cases-file tools/llm_compare_cases.example.json --runs-per-model 5 --concurrency 4 --output-json /tmp/llm_compare_report.json`

Per-model config supports:
- `token_param`: `max_completion_tokens` or `max_tokens`
- `max_output_tokens`: override token cap for that model

## Notes for Interviewers
- This repository intentionally preserves core behavior while improving architecture.
- Refactor work focused on maintainability and technical debt reduction first.
- Optimization and production hardening are the next deliberate phase.
