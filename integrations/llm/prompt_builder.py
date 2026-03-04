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


def _prune_for_prompt(detections: List[Dict[str, Any]], depth_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
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
    kept_labels = {det.get("class") for _, det in kept if det.get("class")}
    filtered_detections = [det for _, det in kept]

    if not isinstance(depth_data, dict):
        return filtered_detections, depth_data

    filtered_depth = json.loads(json.dumps(depth_data))
    if isinstance(filtered_depth.get("collisionAnalysis"), list):
        filtered_depth["collisionAnalysis"] = [
            item
            for item in filtered_depth["collisionAnalysis"]
            if item.get("objectId") in kept_ids
        ]
    if isinstance(filtered_depth.get("objects_with_depth"), list):
        filtered_depth["objects_with_depth"] = [
            item
            for item in filtered_depth["objects_with_depth"]
            if item.get("label") in kept_labels
        ]

    return filtered_detections, filtered_depth


def create_prompt(detections, depth_data, query, is_auto_detect):
    detections, depth_data = _prune_for_prompt(detections or [], depth_data or {})
    detections_json = json.dumps(detections, indent=2)
    depth_json = json.dumps(depth_data, indent=2)

    if is_auto_detect:
        return f"""
        Mode: Scene description
        Task: Briefly describe the most relevant nearby objects.

        ### DETECTED OBJECTS:
        {detections_json}

        ### DEPTH / SPATIAL DATA:
        {depth_json}
        """

    if not query:
        raise ValueError("Query is required for regular mode")

    return f"""
        Mode: Query response
        Task: Answer the user question from detections and spatial data.

        ### USER QUERY:
        {query}

        ### DETECTED OBJECTS:
        {detections_json}

        ### DEPTH / SPATIAL DATA:
        {depth_json}
        """
