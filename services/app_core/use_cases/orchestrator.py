import logging
import sys
from time import perf_counter
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root.parent) not in sys.path:
    sys.path.insert(0, str(project_root.parent))

from services.app_core.observability import ensure_trace_id, get_logger, log_event, stage_timer
from integrations.llm.azure_responder import azure_auto_detect, azure_respond
from services.perception.pipeline.runner import run_perception_pipeline

logger = get_logger(__name__)

def process_query(text_query: str, image_path: str, trace_id: str | None = None) -> dict:
    trace_id = ensure_trace_id(trace_id)
    timings_ms = {}
    total_start = perf_counter()

    try:
        with stage_timer(timings_ms, "perception_ms"):
            perception_result = run_perception_pipeline(image_path, trace_id=trace_id)

        detections = perception_result["detections"]
        depth_data = perception_result["depth_data"]
        timings_ms.update(perception_result.get("timings_ms", {}))

        if not depth_data:
            depth_data = {
                "objects_with_depth": [
                    {"label": det["class"], "relative_depth": 0.5}
                    for det in detections
                ]
            }

        with stage_timer(timings_ms, "llm_ms"):
            response_text = azure_respond(
                query=text_query,
                detections=detections,
                depth_data=depth_data,
                trace_id=trace_id,
            )

        timings_ms["total_ms"] = round((perf_counter() - total_start) * 1000, 2)
        log_event(
            logger,
            "pipeline_completed",
            trace_id=trace_id,
            timings_ms=timings_ms,
        )
        return {"response_text": response_text, "timings_ms": timings_ms, "trace_id": trace_id}
    except Exception as e:
        timings_ms["total_ms"] = round((perf_counter() - total_start) * 1000, 2)
        log_event(
            logger,
            "pipeline_failed",
            level=logging.ERROR,
            trace_id=trace_id,
            timings_ms=timings_ms,
        )
        logger.exception("process_query_failed")
        return {"response_text": f"Error: {str(e)}", "timings_ms": timings_ms, "trace_id": trace_id}


def process_auto_detect(image_path: str, trace_id: str | None = None) -> dict:
    trace_id = ensure_trace_id(trace_id)
    timings_ms = {}
    total_start = perf_counter()

    try:
        with stage_timer(timings_ms, "perception_ms"):
            perception_result = run_perception_pipeline(image_path, trace_id=trace_id)

        detections = perception_result["detections"]
        depth_data = perception_result["depth_data"]
        timings_ms.update(perception_result.get("timings_ms", {}))

        with stage_timer(timings_ms, "llm_ms"):
            response_text = azure_auto_detect(
                detections=detections,
                depth_data=depth_data,
                trace_id=trace_id,
            )

        timings_ms["total_ms"] = round((perf_counter() - total_start) * 1000, 2)
        log_event(
            logger,
            "pipeline_completed",
            trace_id=trace_id,
            timings_ms=timings_ms,
        )
        return {"response_text": response_text, "timings_ms": timings_ms, "trace_id": trace_id}
    except Exception as e:
        timings_ms["total_ms"] = round((perf_counter() - total_start) * 1000, 2)
        log_event(
            logger,
            "pipeline_failed",
            level=logging.ERROR,
            trace_id=trace_id,
            timings_ms=timings_ms,
        )
        logger.exception("process_auto_detect_failed")
        return {"response_text": f"Error: {str(e)}", "timings_ms": timings_ms, "trace_id": trace_id}
