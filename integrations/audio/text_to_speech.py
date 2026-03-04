import os
import base64
from time import perf_counter
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from services.app_core.observability import ensure_trace_id, get_logger, log_event

load_dotenv()
logger = get_logger(__name__)

DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Qggl4b0xRMiqOwhPtVWT")
DEFAULT_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is not set")

elevenlabs = ElevenLabs(api_key=api_key)


def text_to_speech(text: str, voice_id: str = DEFAULT_VOICE_ID, trace_id: str | None = None) -> dict:
    trace_id = ensure_trace_id(trace_id)
    start = perf_counter()
    audio_stream = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=DEFAULT_MODEL_ID,
        output_format="mp3_44100_128",
    )
    audio = b"".join(audio_stream)
    tts_ms = round((perf_counter() - start) * 1000, 2)
    log_event(
        logger,
        "tts_completed",
        trace_id=trace_id,
        timings_ms={"tts_synthesis_ms": tts_ms},
    )
    return {
        "ok": True,
        "audio_base64": base64.b64encode(audio).decode("utf-8"),
        "content_type": "audio/mpeg",
        "bytes_generated": len(audio),
        "voice_id": voice_id,
        "model_id": DEFAULT_MODEL_ID,
        "tts_synthesis_ms": tts_ms,
    }
