import logging


def capture_from_usb_mic() -> bytes:
    """Stub: capture audio from USB microphone. Returns WAV bytes."""
    logging.warning("capture_from_usb_mic: not implemented")
    return b""


def receive_wav_from_arduino() -> bytes:
    """Stub: receive WAV audio chunk sent over TCP from Arduino. Returns WAV bytes."""
    logging.warning("receive_wav_from_arduino: not implemented")
    return b""


def get_audio() -> bytes:
    """Returns a WAV audio chunk for transcription. Swap stub when audio source is decided."""
    return capture_from_usb_mic()
