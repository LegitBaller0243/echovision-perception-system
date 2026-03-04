# LLM Evaluation Summary

This folder contains the reproducible artifacts for our model comparison work:
- test cases
- test images
- summary metrics

## Compared Models

Run context:
- 4 models compared on the same case set
- 2 runs per model per case
- shared prompt and identical perception payload shape

| Model | Success Rate | Avg Latency (ms) | P95 Latency (ms) | Avg Total Tokens | Notes |
|---|---:|---:|---:|---:|---|
| Meta-Llama-3.1-8B-Instruct | 1.00 | 664.85 | 1228.83 | 765.38 | Fastest average latency, but response quality varied in some runs. |
| gpt-4o-mini | 1.00 | 795.75 | 1561.87 | 745.00 | Selected default model for production balance. |
| mistral-small-2503 | 1.00 | 918.04 | 1509.29 | 921.38 | Good responses, but heavier token usage. |
| DeepSeek-V3.2 | 1.00 | 1714.72 | 2354.21 | 746.25 | Strong responses, slowest in this run. |

## Decision

Current default model: `gpt-4o-mini`.

## Re-run

Use:

```bash
.venv/bin/python tools/llm_compare.py \
  --cases-file llm_evaluation/cases/cases_v1.json \
  --models-file tools/llm_compare_models.example.json \
  --runs-per-model 2 \
  --concurrency 4 \
  --log-perception \
  --output-json /tmp/llm_compare_report.json
```

Notes:
- Raw comparison JSON should be treated as generated output and kept out of git.
- Do not commit endpoint/key-bearing logs.
