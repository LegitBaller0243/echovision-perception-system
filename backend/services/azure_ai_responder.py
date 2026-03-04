import sys
from pathlib import Path

# Add project root to path to import prompt_responder
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from prompt_responder.llm_response import get_response


def azure_respond(query: str, detections: list, depth_data: dict) -> str:
    """Get response for regular user query."""
    return get_response(detections, depth_data, query=query, is_auto_detect=False)


def azure_auto_detect(detections: list, depth_data: dict) -> str:
    """Get response for automatic detection alert."""
    return get_response(detections, depth_data, query=None, is_auto_detect=True)