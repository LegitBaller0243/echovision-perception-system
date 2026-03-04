# Text-to-speech conversion using ElevenLabs API
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from playsound import playsound
import tempfile
load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is not set")

elevenlabs = ElevenLabs(api_key=api_key)


def text_to_speech(text: str, voice_id: str = "Qggl4b0xRMiqOwhPtVWT") -> bytes:
    audio = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    audio = b"".join(audio)

    with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as tmp:
        tmp.write(audio)
        tmp.flush()  # ensure all data is written
        playsound(tmp.name)