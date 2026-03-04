import os
import base64
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Qggl4b0xRMiqOwhPtVWT")
DEFAULT_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is not set")

elevenlabs = ElevenLabs(api_key=api_key)


def text_to_speech(text: str, voice_id: str = DEFAULT_VOICE_ID) -> dict:
    audio_stream = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=DEFAULT_MODEL_ID,
        output_format="mp3_44100_128",
    )
    audio = b"".join(audio_stream)
    return {
        "ok": True,
        "audio_base64": base64.b64encode(audio).decode("utf-8"),
        "content_type": "audio/mpeg",
        "bytes_generated": len(audio),
        "voice_id": voice_id,
        "model_id": DEFAULT_MODEL_ID,
    }
