"""
Configuration settings for the SoundSight backend
"""

import os

# Serial port configuration
ENABLE_SERIAL = os.getenv("ENABLE_SERIAL", "1").lower() in ("1", "true", "yes", "on")
SERIAL_PORT = os.getenv("SERIAL_PORT", None)  # Auto-detect if None
SERIAL_BAUD = 115200

# Audio configuration
AUDIO_SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # Mono
AUDIO_CHUNK_DURATION = 0.5  # seconds
AUDIO_CHUNK_SIZE = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_DURATION)

# Voice Activity Detection (VAD) thresholds
VAD_START_THRESHOLD = 0.02  # RMS energy to start detecting speech
VAD_STOP_THRESHOLD = 0.01   # RMS energy to stop detecting speech
VAD_HANGOVER_BLOCKS = 3     # Number of blocks to wait after energy drops below stop threshold

# Direction gating parameters
DIRECTION_STABLE_MS = 400    # Direction must be stable for this duration
MIN_CONFIDENCE = 0.20        # Minimum confidence to emit caption
MIN_ENERGY = 0.015           # Minimum RMS energy to emit caption

# Speech-to-Text (Whisper) configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny, base, small, medium, large
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu or cuda
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, int8_float16, float16, float32

# TCP client configuration (connect to existing Unity/Arduino TCP server)
TCP_HOST = os.getenv("TCP_HOST", "10.29.193.69")
TCP_PORT = int(os.getenv("TCP_PORT", "7000"))
TCP_MESSAGE_FORMAT = os.getenv("TCP_MESSAGE_FORMAT", "text").lower()
TCP_FRAME_PREFIX = os.getenv("TCP_FRAME_PREFIX", "S")
TCP_FRAME_SUFFIX = os.getenv("TCP_FRAME_SUFFIX", "E\n")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
