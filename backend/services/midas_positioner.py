import base64
import io
import os
import tempfile
import numpy as np
from PIL import Image
from typing import Dict, List

from .depth_estimator import depth_estimate
from .collision_detector import collision_analyze

def _is_base64_string(data: str) -> bool:
    """Check if string is likely base64 encoded."""
    # Base64 strings are typically long and contain only base64 characters
    if len(data) < 100:
        return False
    # Check if it looks like base64 (alphanumeric + / + =)
    base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    return all(c in base64_chars or c.isspace() for c in data[:200])

def _clean_base64(data: str) -> str:
    """Clean base64 string by removing prefix and fixing padding."""
    if data.startswith("data:image"):
        data = data.split(",", 1)[1]  # remove "data:image/jpeg;base64,"
    # Fix padding if necessary
    missing_padding = len(data) % 4
    if missing_padding:
        data += "=" * (4 - missing_padding)
    return data

def positioner(image_path: str, detections: Dict) -> Dict:
    """
    Process image for depth estimation and collision detection.
    
    Args:
        image_path: Either a file path or base64 encoded image string
        detections: YOLO detection results dictionary
        
    Returns:
        Dictionary with depth stats and collision analysis
    """
    temp_file_path = None
    try:
        print(f"\n[midas_positioner] Processing image input (length: {len(image_path)})")
        
        # === 1. Determine if input is file path or base64 string ===
        if os.path.exists(image_path):
            # It's a file path - use it directly
            print(f"[midas_positioner] Using file path: {image_path}")
            actual_image_path = image_path
        elif _is_base64_string(image_path):
            # It's a base64 string - decode and save to temp file
            print("[midas_positioner] Detected base64 string, decoding...")
            try:
                clean_b64 = _clean_base64(image_path)
                image_bytes = base64.b64decode(clean_b64, validate=True)
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                
                # Save to temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                image.save(temp_file.name, 'JPEG')
                temp_file.close()
                actual_image_path = temp_file.name
                temp_file_path = actual_image_path
                print(f"[midas_positioner] Decoded base64 to temp file: {actual_image_path}")
            except Exception as e:
                raise ValueError(f"Failed to decode base64 image: {str(e)}")
        else:
            raise ValueError(f"Invalid image input: neither a valid file path nor base64 string")

        # === 2. Estimate depth map using MiDaS ===
        print("[midas_positioner] Running depth estimation...")
        depth_result = depth_estimate(actual_image_path)
        depth_map = depth_result["depthMap"]
        if not isinstance(depth_map, np.ndarray):
            raise ValueError("Depth map is not a numpy array.")
        print(f"[midas_positioner] Depth map shape: {depth_map.shape}")

        # === 3. Format YOLO detections ===
        labeled_objects: List[Dict] = []
        # Handle both dict with "Objects" key and direct list
        if isinstance(detections, dict):
            detections_list = detections.get("Objects", [])
        elif isinstance(detections, list):
            detections_list = detections
        else:
            detections_list = []
        
        print(f"[midas_positioner] Processing {len(detections_list)} detections")
        for i, det in enumerate(detections_list):
            pos = det.get("position", {})
            labeled_objects.append({
                "objectId": i + 1,
                "label": det.get("class", "unknown"),
                "bbox": [
                    float(pos.get("x1", 0)),
                    float(pos.get("y1", 0)),
                    float(pos.get("x2", 0)),
                    float(pos.get("y2", 0)),
                ],
                "detectionConfidence": float(det.get("confidence", 0.0))
            })

        # === 4. Run collision detection ===
        print(f"[midas_positioner] Running collision analysis on {len(labeled_objects)} objects...")
        collision_results = collision_analyze(depth_map, labeled_objects)
        print(f"[midas_positioner] Collision analysis complete: {len(collision_results)} results")

        # === 5. Build unified response ===
        result = {
            "depthStats": depth_result.get("stats", {}),
            "inferenceTime": depth_result.get("inferenceTime", 0.0),
            "collisionAnalysis": collision_results
        }
        print("[midas_positioner] Successfully completed processing")
        return result

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[midas_positioner] Error: {error_msg}")
        traceback.print_exc()
        return {
            "error": error_msg,
            "depthStats": {},
            "collisionAnalysis": []
        }
    finally:
        # Clean up temp file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"[midas_positioner] Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                print(f"[midas_positioner] Warning: Failed to delete temp file: {e}")
