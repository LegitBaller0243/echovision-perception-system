import sys
import json
from pathlib import Path
import traceback

project_root = Path(__file__).parent.parent.parent
if str(project_root.parent) not in sys.path:
    sys.path.insert(0, str(project_root.parent))

from integrations.llm.azure_responder import azure_auto_detect, azure_respond
from services.perception.pipeline.runner import run_perception_pipeline


def process_query(text_query: str, image_path: str) -> dict:
    print("\n[process_query] Starting query pipeline...")
    print(f"[process_query] Image path: {image_path}")
    try:
        perception_result = run_perception_pipeline(image_path)
        yolo_results = perception_result["yolo_results"]
        print("[process_query] YOLO results:", json.dumps(yolo_results, indent=2))

        detections = perception_result["detections"]
        depth_data = perception_result["depth_data"]
        if not depth_data:
            print("[process_auto_detect] No depth data, using fallback structure.")
            depth_data = {
                "objects_with_depth": [
                    {"label": det["class"], "relative_depth": 0.5}
                    for det in detections
                ]
            }

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
        perception_result = run_perception_pipeline(image_path)
        yolo_results = perception_result["yolo_results"]
        print("[process_auto_detect] YOLO results:", json.dumps(yolo_results, indent=2))

        detections = perception_result["detections"]
        depth_data = perception_result["depth_data"]
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
