# Speech-to-text transcription using ElevenLabs API
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is not set")

elevenlabs = ElevenLabs(api_key=api_key)


def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
            tag_audio_events=True, # Tag audio events like laughter, applause, etc.
            language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
            diarize=True, # Whether to annotate who is speaking
        )
    return transcription
