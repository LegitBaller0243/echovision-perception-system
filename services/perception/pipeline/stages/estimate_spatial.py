from typing import Dict, List

from services.perception.pipeline.positioner import positioner


def estimate_spatial(image_path: str, detections: List[Dict]) -> Dict:
    """Stage 2: depth estimation and collision analysis."""
    return positioner(image_path, detections)
