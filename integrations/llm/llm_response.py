import json
import os
from typing import Any, Dict, List, Optional
from openai import AzureOpenAI
from dotenv import load_dotenv
from integrations.llm.prompt_builder import SPATIAL_SYSTEM_PROMPT, create_prompt

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
# AZURE CALL
# ---------------------------------------------------------------------
def ask_azure(prompt):
    print("[azure_ai_responder] Sending prompt to Azure...")

    messages = [
        {"role": "system", "content": SPATIAL_SYSTEM_PROMPT},
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

    prompt = create_prompt(detections, depth_data, query, is_auto_detect)
    log_prompt(prompt)
    response = ask_azure(prompt)

    print("[azure_ai_responder] Final response text:", response)
    return response
