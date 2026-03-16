import collections
import logging
import os
import time

from audio import get_audio
from arduino_client import ArduinoClient
from ar_server import ARServer
from vad_batcher import VADBatcher
from whisper_client import transcribe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARDUINO_BRIDGE_HOST = os.environ.get("ARDUINO_BRIDGE_HOST", "127.0.0.1")
ARDUINO_BRIDGE_PORT = int(os.environ.get("ARDUINO_BRIDGE_PORT", "7000"))
AR_HOST       = os.environ.get("AR_HOST", "0.0.0.0")
AR_PORT       = int(os.environ.get("AR_PORT", "9001"))
POLL_INTERVAL  = float(os.environ.get("POLL_INTERVAL", "1.0"))
CLIP_DEBUG_DIR = os.environ.get("CLIP_DEBUG_DIR", "/tmp/vad_clips")
CLIP_DEBUG_MAX = 3

# Set to True to use the Arduino's onboard mics (VAD-batched via bridge_shim).
# Set to False to use the USB mic via sounddevice.
USE_ARDUINO_MIC = os.environ.get("USE_ARDUINO_MIC", "false").lower() == "true"
LOG_DIRECTION   = os.environ.get("LOG_DIRECTION", "false").lower() == "true"


_clip_ring: collections.deque[str] = collections.deque(maxlen=CLIP_DEBUG_MAX)
_clip_counter = 0


def _save_debug_clip(audio: bytes) -> str:
    global _clip_counter
    _clip_counter += 1
    os.makedirs(CLIP_DEBUG_DIR, exist_ok=True)
    path = os.path.join(CLIP_DEBUG_DIR, f"clip_{_clip_counter:04d}.wav")
    with open(path, "wb") as f:
        f.write(audio)
    if len(_clip_ring) == _clip_ring.maxlen:
        try:
            os.remove(_clip_ring[0])
        except OSError:
            pass
    _clip_ring.append(path)
    logging.info(f"Saved debug clip: {path}")
    return path


def main():
    ar_server = ARServer(AR_HOST, AR_PORT)
    ar_server.start()

    vad_batcher = VADBatcher() if USE_ARDUINO_MIC else None

    def on_arduino_message(topic: str, data: dict):
        if topic == "direction":
            if LOG_DIRECTION:
                print(f"[arduino] direction: {data}", flush=True)
            ar_server.broadcast({
                "type": "direction",
                "direction": data.get("direction", "none"),
                "volume": data.get("volume", 0),
                "timestamp": time.time(),
            })
        elif topic == "audio" and vad_batcher is not None:
            vad_batcher.feed(data.get("samples", []))

    arduino = ArduinoClient(ARDUINO_BRIDGE_HOST, ARDUINO_BRIDGE_PORT, on_message=on_arduino_message)
    arduino.start()

    mic_source = "arduino (VAD)" if USE_ARDUINO_MIC else "USB (VAD)"
    logging.info(f"Pipeline running (mic source: {mic_source})")

    if not USE_ARDUINO_MIC:
        audio.list_devices()

    while True:
        if USE_ARDUINO_MIC:
            audio = vad_batcher.get_segment()
            arduino_data = arduino.get_latest()
            arduino_data.pop("audio", None)
        else:
            audio = get_audio()
            arduino_data = arduino.get_latest()
            arduino_data.pop("audio", None)

        if not audio:
            time.sleep(POLL_INTERVAL)
            continue

        _save_debug_clip(audio)
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


if __name__ == "__main__":
    main()
