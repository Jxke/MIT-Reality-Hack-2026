import logging
import os
import time

from audio import get_audio
from arduino_client import ArduinoClient
from ar_server import ARServer
from whisper_client import transcribe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARDUINO_HOST = os.environ.get("ARDUINO_HOST", "localhost")
ARDUINO_PORT = int(os.environ.get("ARDUINO_PORT", "9000"))
AR_HOST = os.environ.get("AR_HOST", "0.0.0.0")
AR_PORT = int(os.environ.get("AR_PORT", "9001"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))


def main():
    arduino = ArduinoClient(ARDUINO_HOST, ARDUINO_PORT)
    ar_server = ARServer(AR_HOST, AR_PORT)

    arduino.start()
    ar_server.start()

    logging.info("Pipeline running")

    while True:
        audio = get_audio()
        if not audio:
            time.sleep(POLL_INTERVAL)
            continue

        text = transcribe(audio)
        arduino_data = arduino.get_latest()

        if text or arduino_data:
            message = {"text": text, **arduino_data}
            logging.info(f"Broadcasting: {message}")
            ar_server.broadcast(message)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
