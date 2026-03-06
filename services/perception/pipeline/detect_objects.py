from typing import List, Dict

from services.perception.inference.yolo.adapter import yolo_detect


def detect_objects(image_path: str) -> List[Dict]:
    """Stage 1: object detection."""
    return yolo_detect(image_path).get("Objects", [])
