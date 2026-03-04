#!/usr/bin/env python3
import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integrations.llm.prompt_builder import SPATIAL_SYSTEM_PROMPT, create_prompt


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_case(
    case_file: str,
    query: Optional[str],
    detections_file: Optional[str],
    depth_file: Optional[str],
    is_auto_detect: bool,
) -> Dict[str, Any]:
    if case_file:
        data = read_json(case_file)
        required = ["detections", "depth_data", "is_auto_detect"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Case file missing keys: {missing}")
        if not data["is_auto_detect"] and not data.get("query"):
            raise ValueError("Case file requires `query` when is_auto_detect is false")
        return data

    if not detections_file or not depth_file:
        raise ValueError(
            "Either --case-file OR both --detections-file and --depth-file are required."
        )

    detections = read_json(detections_file)
    depth_data = read_json(depth_file)
    if not is_auto_detect and not query:
        raise ValueError("--query is required when --is-auto-detect is false")

    return {
        "query": query,
        "detections": detections,
        "depth_data": depth_data,
        "is_auto_detect": is_auto_detect,
    }


def case_from_image(image_path: str, query: Optional[str], is_auto_detect: bool) -> Dict[str, Any]:
    if not is_auto_detect and not query:
        raise ValueError("--query is required for query mode when using --image-path")

    from services.perception.pipeline.runner import run_perception_pipeline

    perception_result = run_perception_pipeline(image_path)
    yolo_results = perception_result.get("yolo_results")
    detections = perception_result.get("detections", [])
    depth_data = perception_result.get("depth_data")
    if not depth_data:
        depth_data = {
            "objects_with_depth": [
                {"label": det.get("class", "unknown"), "relative_depth": 0.5}
                for det in detections
            ]
        }

    return {
        "query": query,
        "yolo_results": yolo_results,
        "detections": detections,
        "depth_data": depth_data,
        "is_auto_detect": is_auto_detect,
        "source_image": image_path,
    }


def load_cases(cases_file: str, query: Optional[str], is_auto_detect: bool) -> List[Dict[str, Any]]:
    data = read_json(cases_file)
    if not isinstance(data, list) or not data:
        raise ValueError("cases-file must contain a non-empty JSON array")

    cases: List[Dict[str, Any]] = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Case at index {idx} must be an object")

        if entry.get("image_path"):
            case = case_from_image(
                image_path=entry["image_path"],
                query=entry.get("query", query),
                is_auto_detect=entry.get("is_auto_detect", is_auto_detect),
            )
            case["case_name"] = entry.get("case_name") or f"case_{idx+1}"
            cases.append(case)
            continue

        required = ["detections", "depth_data", "is_auto_detect"]
        missing = [k for k in required if k not in entry]
        if missing:
            raise ValueError(f"Case at index {idx} missing keys: {missing}")
        if not entry["is_auto_detect"] and not entry.get("query"):
            raise ValueError(f"Case at index {idx} requires `query` when is_auto_detect is false")
        entry_case = dict(entry)
        entry_case["case_name"] = entry.get("case_name") or f"case_{idx+1}"
        cases.append(entry_case)

    return cases


def build_client(model_cfg: Dict[str, Any]):
    provider = model_cfg["provider"]
    api_key_env = model_cfg["api_key_env"]
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"Missing env var: {api_key_env}")

    if provider == "openai":
        return OpenAI(api_key=api_key)

    if provider == "openai_compat":
        base_url_env = model_cfg.get("base_url_env")
        base_url = os.getenv(base_url_env) if base_url_env else model_cfg.get("base_url")
        if not base_url:
            if base_url_env:
                raise ValueError(f"openai_compat model missing env var: {base_url_env}")
            raise ValueError("openai_compat model requires `base_url` or `base_url_env`")
        return OpenAI(api_key=api_key, base_url=base_url)

    if provider == "azure":
        endpoint_env = model_cfg.get("azure_endpoint_env", "AZURE_OPENAI_ENDPOINT")
        endpoint = os.getenv(endpoint_env) or model_cfg.get("azure_endpoint")
        if not endpoint:
            raise ValueError(
                f"Azure model needs endpoint via {endpoint_env} or `azure_endpoint` in config"
            )
        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=model_cfg.get("api_version", "2024-12-01-preview"),
        )

    raise ValueError(f"Unsupported provider: {provider}")


def extract_text(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def resolve_model_name(model_cfg: Dict[str, Any]) -> str:
    model_env = model_cfg.get("model_env")
    if model_env:
        model = os.getenv(model_env)
        if not model:
            raise ValueError(f"Missing env var: {model_env}")
        return model

    model = model_cfg.get("model")
    if not model:
        raise ValueError("Model config requires either `model` or `model_env`")
    return model


def usage_to_dict(response: Any) -> Dict[str, Optional[int]]:
    usage = getattr(response, "usage", None)
    if not usage:
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def select_token_param(model_cfg: Dict[str, Any], model_name: str) -> str:
    token_param = model_cfg.get("token_param")
    if token_param in {"max_completion_tokens", "max_tokens"}:
        return token_param
    if "mistral" in model_name.lower():
        return "max_tokens"
    return "max_completion_tokens"


def resolve_max_tokens(model_cfg: Dict[str, Any], default_tokens: int) -> int:
    value = model_cfg.get("max_output_tokens", default_tokens)
    try:
        return int(value)
    except Exception:
        return default_tokens


def call_once(model_cfg: Dict[str, Any], prompt: str, max_completion_tokens: int, case_name: str) -> Dict[str, Any]:
    name = model_cfg["name"]
    model = model_cfg.get("model")
    try:
        model = resolve_model_name(model_cfg)
        client = build_client(model_cfg)
        start = time.perf_counter()

        token_param = select_token_param(model_cfg, model)
        token_limit = resolve_max_tokens(model_cfg, max_completion_tokens)
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SPATIAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            token_param: token_limit,
        }

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as e:
            # Some providers reject max_completion_tokens and require max_tokens.
            if token_param == "max_completion_tokens" and (
                "max_completion_tokens" in str(e) or "max_tokens" in str(e)
            ):
                kwargs.pop("max_completion_tokens", None)
                kwargs["max_tokens"] = token_limit
                response = client.chat.completions.create(**kwargs)
            else:
                raise

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        text = extract_text(response)
        usage = usage_to_dict(response)
        return {
            "name": name,
            "provider": model_cfg["provider"],
            "model": model,
            "case_name": case_name,
            "success": True,
            "latency_ms": latency_ms,
            "response_text": text,
            "response_chars": len(text or ""),
            **usage,
            "error": None,
        }
    except Exception as e:
        return {
            "name": name,
            "provider": model_cfg.get("provider"),
            "model": model_cfg.get("model"),
            "case_name": case_name,
            "success": False,
            "latency_ms": None,
            "response_text": "",
            "response_chars": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "error": str(e),
        }


def run_comparison(
    models: List[Dict[str, Any]],
    prompt: str,
    case_name: str,
    max_completion_tokens: int,
    runs_per_model: int,
    concurrency: int,
) -> List[Dict[str, Any]]:
    jobs = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for model_cfg in models:
            for _ in range(runs_per_model):
                jobs.append(
                    pool.submit(call_once, model_cfg, prompt, max_completion_tokens, case_name)
                )

        results = [job.result() for job in as_completed(jobs)]
    return results


def summarize_results(
    models: List[Dict[str, Any]], results: List[Dict[str, Any]], expected_runs_per_model: int
) -> List[Dict[str, Any]]:
    successful = [r for r in results if r["success"]]
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in successful:
        grouped.setdefault(r["name"], []).append(r)

    summary: List[Dict[str, Any]] = []
    for model_cfg in models:
        name = model_cfg["name"]
        try:
            resolved_model = resolve_model_name(model_cfg)
        except Exception:
            resolved_model = model_cfg.get("model")
        runs = grouped.get(name, [])
        if not runs:
            first_error = next((r for r in results if r["name"] == name and not r["success"]), None)
            summary.append(
                {
                    "name": name,
                    "provider": model_cfg["provider"],
                    "model": resolved_model,
                    "success_rate": 0.0,
                    "avg_latency_ms": None,
                    "p95_latency_ms": None,
                    "avg_total_tokens": None,
                    "sample_response": "",
                    "error": first_error["error"] if first_error else "No successful runs",
                }
            )
            continue

        latencies = sorted(r["latency_ms"] for r in runs if r["latency_ms"] is not None)
        p95_index = max(0, min(len(latencies) - 1, math.ceil(len(latencies) * 0.95) - 1))
        total_tokens = [r["total_tokens"] for r in runs if r["total_tokens"] is not None]
        first_error = next((r for r in results if r["name"] == name and not r["success"]), None)

        summary.append(
            {
                "name": name,
                "provider": model_cfg["provider"],
                "model": resolved_model,
                "success_rate": round(len(runs) / expected_runs_per_model, 2),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
                "p95_latency_ms": latencies[p95_index],
                "avg_total_tokens": round(sum(total_tokens) / len(total_tokens), 2)
                if total_tokens
                else None,
                "sample_response": runs[0]["response_text"],
                "error": first_error["error"] if first_error else None,
            }
        )

    summary.sort(key=lambda x: float("inf") if x["avg_latency_ms"] is None else x["avg_latency_ms"])
    return summary


def print_summary(summary: List[Dict[str, Any]], preview_chars: int):
    print("\n=== LLM Comparison Summary (sorted by avg latency) ===")
    for row in summary:
        print(
            f"- {row['name']} [{row['provider']}/{row['model']}]: "
            f"success_rate={row['success_rate']}, "
            f"avg_latency_ms={row['avg_latency_ms']}, "
            f"p95_latency_ms={row['p95_latency_ms']}, "
            f"avg_total_tokens={row['avg_total_tokens']}"
        )
        if row["error"]:
            print(f"  error: {row['error']}")
        preview = (row["sample_response"] or "").replace("\n", " ").strip()
        if preview:
            print(f"  sample: {preview[:preview_chars]}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare multiple LLM models/providers side-by-side for the same perception prompt."
    )
    parser.add_argument(
        "--models-file",
        default="tools/llm_compare_models.example.json",
        help="Path to JSON array of model configs",
    )
    parser.add_argument(
        "--case-file",
        default="tools/llm_compare_case.example.json",
        help="Path to JSON with detections/depth/query/is_auto_detect",
    )
    parser.add_argument(
        "--cases-file",
        default=None,
        help="Path to JSON array of case objects (supports inline case data or image_path entries)",
    )
    parser.add_argument("--query", default=None)
    parser.add_argument("--detections-file", default=None)
    parser.add_argument("--depth-file", default=None)
    parser.add_argument("--image-path", default=None, help="Build a case from image via YOLO+MiDaS")
    parser.add_argument("--is-auto-detect", action="store_true")
    parser.add_argument("--runs-per-model", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-completion-tokens", type=int, default=180)
    parser.add_argument("--preview-chars", type=int, default=220)
    parser.add_argument(
        "--log-perception",
        action="store_true",
        help="Print per-case YOLO detections and depth payload before model calls",
    )
    parser.add_argument("--output-json", default=None, help="Optional output path for full JSON report")
    args = parser.parse_args()

    load_dotenv()

    models = read_json(args.models_file)
    if not isinstance(models, list) or not models:
        raise ValueError("models-file must contain a non-empty JSON array")

    if args.cases_file:
        cases = load_cases(args.cases_file, query=args.query, is_auto_detect=args.is_auto_detect)
    elif args.image_path:
        cases = [
            case_from_image(
                image_path=args.image_path,
                query=args.query,
                is_auto_detect=args.is_auto_detect,
            )
        ]
        cases[0]["case_name"] = "image_case_1"
    else:
        case = load_case(
            case_file=args.case_file,
            query=args.query,
            detections_file=args.detections_file,
            depth_file=args.depth_file,
            is_auto_detect=args.is_auto_detect,
        )
        case["case_name"] = "case_1"
        cases = [case]

    all_raw_results: List[Dict[str, Any]] = []
    prompts: List[Dict[str, str]] = []
    cases_metadata: List[Dict[str, Any]] = []
    for case in cases:
        case_meta = {
            "case_name": case["case_name"],
            "is_auto_detect": case["is_auto_detect"],
            "query": case.get("query"),
            "source_image": case.get("source_image"),
            "yolo_results": case.get("yolo_results"),
            "detections": case.get("detections"),
            "depth_data": case.get("depth_data"),
        }
        cases_metadata.append(case_meta)
        if args.log_perception:
            print(f"\n=== Case {case['case_name']} ===")
            if case.get("source_image"):
                print(f"source_image: {case['source_image']}")
            print("YOLO detections:")
            print(json.dumps(case.get("detections"), indent=2))
            print("Depth / spatial:")
            print(json.dumps(case.get("depth_data"), indent=2))

        prompt = create_prompt(
            detections=case["detections"],
            depth_data=case["depth_data"],
            query=case.get("query"),
            is_auto_detect=case["is_auto_detect"],
        )
        prompts.append({"case_name": case["case_name"], "prompt": prompt})
        case_results = run_comparison(
            models=models,
            prompt=prompt,
            case_name=case["case_name"],
            max_completion_tokens=args.max_completion_tokens,
            runs_per_model=args.runs_per_model,
            concurrency=args.concurrency,
        )
        all_raw_results.extend(case_results)

    expected_runs_per_model = args.runs_per_model * len(cases)
    summary = summarize_results(
        models=models,
        results=all_raw_results,
        expected_runs_per_model=expected_runs_per_model,
    )

    print_summary(summary, args.preview_chars)

    if args.output_json:
        payload = {
            "summary": summary,
            "raw_results": all_raw_results,
            "cases_count": len(cases),
            "runs_per_model_per_case": args.runs_per_model,
            "cases": cases_metadata,
            "prompts": prompts,
            "generated_at_unix": time.time(),
        }
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nSaved JSON report: {output_path}")


if __name__ == "__main__":
    main()
