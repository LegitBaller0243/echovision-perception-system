from typing import Dict

from services.app_core.observability import ensure_trace_id, get_logger, log_event, stage_timer
from services.perception.pipeline.stages.detect_objects import detect_objects
from services.perception.pipeline.stages.estimate_spatial import estimate_spatial

logger = get_logger(__name__)

def run_perception_pipeline(image_path: str, trace_id: str | None = None) -> Dict:
    """
    Run modular perception stages:
    1. Object detection (YOLO)
    2. Spatial estimation (MiDaS + collision scoring)
    """
    trace_id = ensure_trace_id(trace_id)
    timings_ms = {}

    with stage_timer(timings_ms, "yolo_ms"):
        yolo_results = detect_objects(image_path)
    detections = yolo_results.get("Objects", [])
    with stage_timer(timings_ms, "spatial_ms"):
        depth_data = estimate_spatial(image_path, detections)

    log_event(
        logger,
        "perception_pipeline_completed",
        trace_id=trace_id,
        timings_ms=timings_ms,
    )

    return {
        "yolo_results": yolo_results,
        "detections": detections,
        "depth_data": depth_data,
        "timings_ms": timings_ms,
    }
