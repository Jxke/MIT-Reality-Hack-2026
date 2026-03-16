import io
import logging
import os
import time

import numpy as np
import soundfile as sf

from audio import get_audio, SAMPLE_RATE
from arduino_client import ArduinoClient
from ar_server import ARServer
from whisper_client import transcribe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARDUINO_BRIDGE_HOST = os.environ.get("ARDUINO_BRIDGE_HOST", "127.0.0.1")
ARDUINO_BRIDGE_PORT = int(os.environ.get("ARDUINO_BRIDGE_PORT", "7000"))
AR_HOST      = os.environ.get("AR_HOST", "0.0.0.0")
AR_PORT      = int(os.environ.get("AR_PORT", "9001"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))

# Set to True to use the Arduino's onboard mics (audio packets from arduino_server).
# Set to False to use the USB mic via sounddevice.
USE_ARDUINO_MIC = os.environ.get("USE_ARDUINO_MIC", "false").lower() == "true"


def _arduino_audio_to_wav(samples: list) -> bytes:
    """Convert Arduino int8 PCM samples to WAV bytes for Whisper."""
    audio = np.array(samples, dtype=np.int8).astype(np.float32) / 128.0
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    buf.seek(0)
    return buf.read()


def main():
    ar_server = ARServer(AR_HOST, AR_PORT)
    ar_server.start()

    def on_arduino_message(topic: str, data: dict):
        print(f"[arduino] {topic}: {data}", flush=True)
        if topic == "direction":
            ar_server.broadcast({
                "type": "direction",
                "direction": data.get("direction", "none"),
                "volume": data.get("volume", 0),
                "timestamp": time.time(),
            })

    arduino = ArduinoClient(ARDUINO_BRIDGE_HOST, ARDUINO_BRIDGE_PORT, on_message=on_arduino_message)
    arduino.start()

    mic_source = "arduino" if USE_ARDUINO_MIC else "USB"
    logging.info(f"Pipeline running (mic source: {mic_source})")

    while True:
        if USE_ARDUINO_MIC:
            arduino_data = arduino.get_latest()
            samples = arduino_data.pop("audio", None)
            audio = _arduino_audio_to_wav(samples) if samples else b""
        else:
            audio = get_audio()
            arduino_data = arduino.get_latest()
            arduino_data.pop("audio", None)

        if not audio:
            time.sleep(POLL_INTERVAL)
            continue

        text = transcribe(audio)

        if text:
            message = {
                "type": "caption",
                "mode": "speech",
                "text": text,
                "isFinal": True,
                "direction": arduino_data.get("direction", "none"),
                "volume": arduino_data.get("volume", 0),
                "timestamp": time.time(),
            }
            logging.info(f"Broadcasting: {message}")
            ar_server.broadcast(message)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
