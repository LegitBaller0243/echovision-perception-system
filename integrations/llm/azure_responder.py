from integrations.llm.llm_response import get_response


def azure_respond(query: str, detections: list, depth_data: dict, trace_id: str | None = None) -> str:
    """Get response for regular user query."""
    return get_response(detections, depth_data, query=query, is_auto_detect=False, trace_id=trace_id)


def azure_auto_detect(detections: list, depth_data: dict, trace_id: str | None = None) -> str:
    """Get response for automatic detection alert."""
    return get_response(detections, depth_data, query=None, is_auto_detect=True, trace_id=trace_id)
