import sys
import json
from pathlib import Path
import traceback

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .midas_positioner import positioner
from .yolo_detector import yolo_detect
from .azure_ai_responder import azure_respond, azure_auto_detect


def process_query(text_query: str, image_path: str) -> dict:
    print("\n[process_query] Starting query pipeline...")
    print(f"[process_query] Image path: {image_path}")
    try:
        yolo_results = yolo_detect(image_path)
        print("[process_query] YOLO results:", json.dumps(yolo_results, indent=2))

        detections = yolo_results["Objects"]
        depth_data = positioner(image_path, detections)
        if not depth_data:
            print("[process_auto_detect] No depth data, using fallback structure.")
            depth_data = {
                "objects_with_depth": [
                    {"label": det["class"], "relative_depth": 0.5}
                    for det in detections
                ]
            }

        depth_data = positioner(image_path, detections)
        print("[process_query] Depth data:", json.dumps(depth_data, indent=2))

        response_text = azure_respond(
            query=text_query,
            detections=detections,
            depth_data=depth_data
        )
        print("[process_query] LLM response:", response_text)

        return {"response_text": response_text}
    except Exception as e:
        print("[process_query] ERROR:", e)
        traceback.print_exc()
        return {"response_text": f"Error: {str(e)}"}


def process_auto_detect(image_path: str) -> dict:
    print("\n[process_auto_detect] Starting auto-detect pipeline...")
    print(f"[process_auto_detect] Image path: {image_path}")
    try:
        yolo_results = yolo_detect(image_path)
        print("[process_auto_detect] YOLO results:", json.dumps(yolo_results, indent=2))

        detections = yolo_results["Objects"]
        depth_data = positioner(image_path, detections)
        print("[process_auto_detect] Depth data:", json.dumps(depth_data, indent=2))

        response_text = azure_auto_detect(
            detections=detections,
            depth_data=depth_data
        )
        print("[process_auto_detect] LLM response:", response_text)

        return {"response_text": response_text}
    except Exception as e:
        print("[process_auto_detect] ERROR:", e)
        traceback.print_exc()
        return {"response_text": f"Error: {str(e)}"}
