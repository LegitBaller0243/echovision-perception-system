from typing import Dict

from services.perception.pipeline.stages.detect_objects import detect_objects
from services.perception.pipeline.stages.estimate_spatial import estimate_spatial


def run_perception_pipeline(image_path: str) -> Dict:
    """
    Run modular perception stages:
    1. Object detection (YOLO)
    2. Spatial estimation (MiDaS + collision scoring)
    """
    yolo_results = detect_objects(image_path)
    detections = yolo_results.get("Objects", [])
    depth_data = estimate_spatial(image_path, detections)

    return {
        "yolo_results": yolo_results,
        "detections": detections,
        "depth_data": depth_data,
    }
