import json
import os
from typing import Any, Dict, List, Optional
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

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
    api_key=api_key
)

ASSISTANT_ID_REGULAR = os.getenv("AGENT_REGULAR_ID")
ASSISTANT_ID_AUTO_DETECT = os.getenv("AGENT_AUTO_DETECT_ID")


# ---------------------------------------------------------------------
# ✅ DEBUG HELPERS
# ---------------------------------------------------------------------
def log_json(title: str, data: dict | list | None):
    print(f"\n[azure_ai_responder] {title}:")
    try:
        print(json.dumps(data, indent=2))
    except Exception:
        print(data)


def log_prompt(prompt: str):
    print("\n" + "=" * 80)
    print("PROMPT SENT TO AZURE:")
    print("=" * 80)
    print(prompt)
    print("=" * 80 + "\n")


# ---------------------------------------------------------------------
# PROMPT CREATION
# ---------------------------------------------------------------------
def create_prompt(detections, depth_data, query, is_auto_detect):
    detections_json = json.dumps(detections, indent=2)
    depth_json = json.dumps(depth_data, indent=2)

    if is_auto_detect:
        prompt = f"""
        You are an automatic spatial awareness assistant for a visually impaired user.
        Analyze the detected objects and spatial data below, and briefly describe what is seen.

        ### DETECTED OBJECTS:
        {detections_json}

        ### DEPTH / SPATIAL DATA:
        {depth_json}
        """
    else:
        if not query:
            raise ValueError("Query is required for regular mode")
        prompt = f"""
        Respond based on the context and data provided below.

        ### USER QUERY:
        {query}

        ### DETECTED OBJECTS:
        {detections_json}

        ### DEPTH / SPATIAL DATA:
        {depth_json}
        """
    
    log_prompt(prompt)
    return prompt


# ---------------------------------------------------------------------
# AZURE CALL
# ---------------------------------------------------------------------
def ask_azure(prompt, assistant_id):
    print(f"[azure_ai_responder] Sending prompt to Azure (assistant_id={assistant_id})...")

    messages = [
        {"role": "system", "content": f"Assistant ID: {assistant_id}"},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            messages=messages,
            max_completion_tokens=512,
            model=deployment,
        )
        # Log the raw response for debugging
        print("\n[azure_ai_responder] Raw Azure response:")
        print(response)

        # Try to parse cleanly
        return response.choices[0].message.content
    except Exception as e:
        print("[azure_ai_responder] ERROR:", e)
        import traceback; traceback.print_exc()
        return f"Error while querying Azure: {e}"


# ---------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------
def get_response(detections, depth_data, query, is_auto_detect):
    log_json("Detections", detections)
    log_json("Depth Data", depth_data)

    assistant_id = ASSISTANT_ID_AUTO_DETECT if is_auto_detect else ASSISTANT_ID_REGULAR
    prompt = create_prompt(detections, depth_data, query, is_auto_detect)
    response = ask_azure(prompt, assistant_id)

    print("[azure_ai_responder] Final response text:", response)
    return response
