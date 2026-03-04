import logging
import os
from time import perf_counter

from openai import AzureOpenAI
from dotenv import load_dotenv

from services.app_core.observability import ensure_trace_id, get_logger, log_event, stage_timer
from integrations.llm.prompt_builder import SPATIAL_SYSTEM_PROMPT, create_prompt

load_dotenv()
logger = get_logger(__name__)

api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
endpoint = "https://samjswag-6951-resource.cognitiveservices.azure.com/"

if not api_key:
    raise ValueError("AZURE_OPENAI_API_KEY environment variable is not set")
if not deployment:
    raise ValueError("MODEL_DEPLOYMENT_NAME environment variable is not set")

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=endpoint,
    api_key=api_key,
)


# ---------------------------------------------------------------------
# AZURE CALL
# ---------------------------------------------------------------------
def ask_azure(prompt: str, trace_id: str | None = None):
    trace_id = ensure_trace_id(trace_id)
    timings_ms = {}

    messages = [
        {"role": "system", "content": SPATIAL_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    try:
        with stage_timer(timings_ms, "azure_llm_ms"):
            response = client.chat.completions.create(
                messages=messages,
                max_completion_tokens=512,
                model=deployment,
            )
        output_text = response.choices[0].message.content
        log_event(
            logger,
            "azure_llm_completed",
            trace_id=trace_id,
            timings_ms=timings_ms,
        )
        return output_text
    except Exception as e:
        log_event(
            logger,
            "azure_llm_failed",
            level=logging.ERROR,
            trace_id=trace_id,
            timings_ms=timings_ms,
        )
        logger.exception("azure_llm_exception")
        return f"Error while querying Azure: {e}"


# ---------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------
def get_response(detections, depth_data, query, is_auto_detect, trace_id: str | None = None):
    trace_id = ensure_trace_id(trace_id)
    total_start = perf_counter()
    prompt = create_prompt(detections, depth_data, query, is_auto_detect)
    response = ask_azure(prompt, trace_id=trace_id)
    total_ms = round((perf_counter() - total_start) * 1000, 2)
    log_event(
        logger,
        "llm_response_generated",
        trace_id=trace_id,
        timings_ms={"llm_total_ms": total_ms},
    )
    return response
