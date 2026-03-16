"""VAD-gated batcher for Arduino int8 PCM audio.

Receives streaming 8 kHz int8 packets via feed(), buffers them into 30 ms
frames, runs webrtcvad on each frame, and enqueues completed speech segments
as WAV bytes for the main loop to dequeue and send to Whisper.

Design mirrors audio.py's record_vad_segment() but operates on a push
(callback-fed) stream rather than a blocking microphone read.
"""

import collections
import io
import logging
import threading

import numpy as np
import soundfile as sf
import webrtcvad

SAMPLE_RATE   = 8000   # Arduino sketch sample rate
FRAME_MS      = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # 240 samples per frame

VAD_MODE         = 2     # 0–3; higher = more aggressive speech/silence distinction
PADDING_MS       = 500   # how much trailing silence to collect before declaring speech end
PADDING_FRAMES   = PADDING_MS // FRAME_MS
PRE_ROLL_MS      = 300   # audio prepended before speech onset to avoid clipping word starts
PRE_ROLL_FRAMES  = PRE_ROLL_MS // FRAME_MS
MIN_SPEECH_MS    = 200   # segments shorter than this are discarded (noise/clicks)
MIN_SPEECH_FRAMES = MIN_SPEECH_MS // FRAME_MS
MAX_SPEECH_MS    = 8000  # force-flush after this duration so Whisper never gets a huge chunk
MAX_SPEECH_FRAMES = MAX_SPEECH_MS // FRAME_MS


class VADBatcher:
    """Thread-safe; feed() is called from ArduinoClient's thread, get_segment()
    from the main loop."""

    def __init__(self):
        self._vad = webrtcvad.Vad(VAD_MODE)
        self._buf: list[int] = []          # raw sample accumulator — drained into frames
        self._pre_roll: collections.deque = collections.deque(maxlen=PRE_ROLL_FRAMES)

        # ring buffer tracks recent speech/silence decisions for onset/end detection
        self._ring: collections.deque = collections.deque(maxlen=PADDING_FRAMES)

        self._voiced_frames: list[list[int]] = []  # frames accumulated during active speech
        self._triggered = False            # True while inside a speech segment
        self._segments: collections.deque[bytes] = collections.deque()  # completed WAV segments
        self._packet_count = 0
        self._lock = threading.Lock()

    def feed(self, samples: list[int]):
        """Feed a packet of signed int8 samples from the Arduino."""
        with self._lock:
            self._packet_count += 1
            # Log periodically so the pipeline logs confirm audio is arriving
            if self._packet_count % 500 == 1:
                logging.info(f"VAD: receiving audio (packet #{self._packet_count})")
            self._buf.extend(samples)
            self._drain()

    def get_segment(self) -> bytes | None:
        """Return the next completed speech WAV, or None if none ready."""
        with self._lock:
            return self._segments.popleft() if self._segments else None

    # ------------------------------------------------------------------ internal

    def _drain(self):
        """Consume as many complete 30 ms frames from _buf as possible."""
        while len(self._buf) >= FRAME_SAMPLES:
            frame = self._buf[:FRAME_SAMPLES]
            self._buf = self._buf[FRAME_SAMPLES:]
            self._process_frame(frame)

    def _process_frame(self, frame: list[int]):
        # webrtcvad requires 16-bit PCM; upshift int8 → int16 before passing in
        is_speech = self._vad.is_speech(_to_pcm16(frame), SAMPLE_RATE)

        if not self._triggered:
            # Pre-speech: maintain a rolling window of recent audio so we can
            # prepend it when speech is detected (avoids clipping word beginnings)
            self._pre_roll.append(frame)
            self._ring.append(is_speech)
            
            # Onset: >90% of the padding window is voiced → speech has started
            if sum(self._ring) > 0.9 * self._ring.maxlen:
                self._triggered = True
                self._voiced_frames.extend(self._pre_roll)
                self._ring.clear()
                logging.info("VAD: speech start detected")
        else:
            self._voiced_frames.append(frame)
            self._ring.append(is_speech)

            too_long = len(self._voiced_frames) >= MAX_SPEECH_FRAMES
            # End: >90% of the padding window is silence → speech has ended
            silence_end = sum(1 for s in self._ring if not s) > 0.9 * self._ring.maxlen

            if silence_end or too_long:
                duration_ms = len(self._voiced_frames) * FRAME_MS
                logging.info(f"VAD: speech end — {duration_ms} ms captured")
                self._flush()

    def _flush(self):
        # Drop segments that are too short to contain real speech
        if len(self._voiced_frames) >= MIN_SPEECH_FRAMES:
            self._segments.append(_to_wav(self._voiced_frames))
        self._voiced_frames = []
        self._triggered = False
        self._ring.clear()


def _to_pcm16(frame: list[int]) -> bytes:
    """int8 → int16 PCM bytes for webrtcvad.

    webrtcvad expects signed 16-bit samples. The Arduino outputs signed 8-bit,
    so we left-shift by 8 bits to fill the upper byte — preserving the signal
    shape while scaling into the int16 range.
    """
    return (np.array(frame, dtype=np.int8).astype(np.int16) << 8).tobytes()


def _to_wav(frames: list[list[int]]) -> bytes:
    """Convert accumulated int8 frames to a peak-normalised WAV for Whisper.

    Peak normalisation boosts quiet mic input to 95% of full scale so Whisper
    receives a strong enough signal to transcribe reliably.
    """
    samples = np.concatenate([np.array(f, dtype=np.int8) for f in frames])
    audio = samples.astype(np.float32) / 128.0
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.95
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    buf.seek(0)
    return buf.read()
