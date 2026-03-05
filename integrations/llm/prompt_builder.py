import json
import os
from typing import Any, Dict, List, Tuple


SPATIAL_SYSTEM_PROMPT = (
    "You are a spatial awareness assistant for a visually impaired user. "
    "Use only provided detections and spatial/depth data. Never invent objects. "
    "Keep responses concise and speech-friendly, ideally one short sentence. "
    "Include direction and relative depth when relevant. "
    "Depth values are relative, not absolute distance. "
    "Do not convert relative depth into meters or feet. "
    "Use natural distance wording like nearby, a bit farther, and far away. "
    "If no user question, briefly describe the most relevant nearby objects. "
    "If there is a question, answer it from provided data only. "
    "If requested object is not detected, say you cannot find it. "
    "Ignore far objects unless explicitly asked. "
    "Respond conversationally, as if speaking directly to the user. "
    "Do not use section labels or rigid templates. "
    "Do not mention technical systems, models, or sensors."
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _compact_detection(det: Dict[str, Any]) -> Dict[str, Any]:
    pos = det.get("position") or {}
    return {
        "class": det.get("class"),
        "confidence": round(_safe_float(det.get("confidence"), 0.0), 3),
        "position": {
            "x1": round(_safe_float(pos.get("x1"), 0.0), 1),
            "y1": round(_safe_float(pos.get("y1"), 0.0), 1),
            "x2": round(_safe_float(pos.get("x2"), 0.0), 1),
            "y2": round(_safe_float(pos.get("y2"), 0.0), 1),
        },
    }


def _compact_collision(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "objectId": item.get("objectId"),
        "label": item.get("label"),
        "direction": item.get("direction"),
        "dangerLevel": item.get("dangerLevel"),
        "confidenceScore": round(_safe_float(item.get("confidenceScore"), 0.0), 3),
    }


def _prune_for_prompt(
    detections: List[Dict[str, Any]], depth_data: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    min_conf = _safe_float(os.getenv("LLM_MIN_CONFIDENCE", "0.45"), default=0.45)
    max_objects = max(1, int(_safe_float(os.getenv("LLM_MAX_OBJECTS", "4"), default=4)))

    ranked = sorted(
        enumerate(detections, start=1),
        key=lambda item: _safe_float(item[1].get("confidence"), default=0.0),
        reverse=True,
    )
    kept = [item for item in ranked if _safe_float(item[1].get("confidence"), default=0.0) >= min_conf]
    if not kept and ranked:
        kept = ranked[:1]
    kept = kept[:max_objects]

    kept_ids = {idx for idx, _ in kept}
    filtered_detections = [_compact_detection(det) for _, det in kept]

    if not isinstance(depth_data, dict):
        return filtered_detections, depth_data

    collision = depth_data.get("collisionAnalysis")
    filtered_collision = []
    if isinstance(collision, list):
        filtered_collision = [
            _compact_collision(item)
            for item in collision
            if item.get("objectId") in kept_ids
        ]

    depth_stats = depth_data.get("depthStats")
    filtered_stats = {}
    if isinstance(depth_stats, dict):
        for key in ("min", "max", "avg"):
            if key in depth_stats:
                filtered_stats[key] = round(_safe_float(depth_stats.get(key), 0.0), 3)

    filtered_depth = {
        "depthStats": filtered_stats,
        "collisionAnalysis": filtered_collision,
    }

    return filtered_detections, filtered_depth


def create_prompt(detections, depth_data, query, is_auto_detect):
    detections, depth_data = _prune_for_prompt(detections or [], depth_data or {})
    detections_json = json.dumps(detections, separators=(",", ":"))
    depth_json = json.dumps(depth_data, separators=(",", ":"))

    if is_auto_detect:
        return (
            "Mode: scene description. Briefly describe nearby relevant objects. "
            f"DETECTIONS={detections_json} DEPTH={depth_json}"
        )

    if not query:
        raise ValueError("Query is required for regular mode")

    return (
        "Mode: query response. Answer only from provided data. "
        f"USER_QUERY={query} DETECTIONS={detections_json} DEPTH={depth_json}"
    )
