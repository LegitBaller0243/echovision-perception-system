import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Dict, List, Tuple

from services.app_core.observability import ensure_trace_id, get_logger, log_event, stage_timer
from services.perception.inference.midas.adapter import depth_estimate
from services.perception.pipeline.spatial_analysis import analyze_depth_and_detections
from services.perception.pipeline.detect_objects import detect_objects

logger = get_logger(__name__)


def _timed_detect(image_path: str) -> Tuple[List[Dict], float]:
    started = perf_counter()
    detections = detect_objects(image_path)
    return detections, round((perf_counter() - started) * 1000, 2)


def _timed_depth(image_path: str) -> Tuple[Dict, float]:
    started = perf_counter()
    depth_result = depth_estimate(image_path)
    return depth_result, round((perf_counter() - started) * 1000, 2)


def run_perception_pipeline(image_path: str, trace_id: str | None = None) -> Dict:
    trace_id = ensure_trace_id(trace_id)
    timings_ms: Dict[str, float] = {}
    parallel_enabled = os.getenv("PERCEPTION_PARALLEL", "1").lower() not in {"0", "false", "off"}

    with stage_timer(timings_ms, "perception_ms"):
        if parallel_enabled:
            with ThreadPoolExecutor(max_workers=2) as pool:
                yolo_future = pool.submit(_timed_detect, image_path)
                depth_future = pool.submit(_timed_depth, image_path)
                detections, timings_ms["yolo_ms"] = yolo_future.result()
                depth_result, timings_ms["midas_ms"] = depth_future.result()
        else:
            detections, timings_ms["yolo_ms"] = _timed_detect(image_path)
            depth_result, timings_ms["midas_ms"] = _timed_depth(image_path)

        with stage_timer(timings_ms, "collision_ms"):
            depth_data = analyze_depth_and_detections(depth_result, detections)

    # Preserve existing benchmark key.
    timings_ms["spatial_ms"] = round(
        timings_ms.get("midas_ms", 0.0) + timings_ms.get("collision_ms", 0.0),
        2,
    )

    log_event(
        logger,
        "perception_pipeline_completed",
        trace_id=trace_id,
        timings_ms=timings_ms,
    )

    return {
        "detections": detections,
        "depth_data": depth_data,
        "timings_ms": timings_ms,
    }
