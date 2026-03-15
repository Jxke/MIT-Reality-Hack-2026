import logging
import os

import requests

WHISPER_URL = os.environ.get("WHISPER_URL", "http://localhost:8080")


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    try:
        resp = requests.post(
            f"{WHISPER_URL}/inference",
            files={"file": (filename, audio_bytes, "audio/wav")},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
    except requests.RequestException as e:
        logging.error(f"Whisper transcription failed: {e}")
        return ""
