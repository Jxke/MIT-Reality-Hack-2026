import collections
import io
import logging
import os
import queue

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad

MIC_INDEX = os.environ.get("MIC_DEVICE_INDEX")
if MIC_INDEX is not None:
    MIC_INDEX = int(MIC_INDEX)

SAMPLE_RATE   = 16000
FRAME_MS      = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
FRAME_BYTES   = FRAME_SAMPLES * 2

VAD_MODE       = 2
PADDING_MS     = 500
PADDING_FRAMES = int(PADDING_MS / FRAME_MS)

PRE_ROLL_MS     = 1000
PRE_ROLL_FRAMES = int(PRE_ROLL_MS / FRAME_MS)

DEBUG_INTERVAL_FRAMES = int(5000 / FRAME_MS)
_debug_frames = []

system_events: queue.Queue = queue.Queue()


def list_devices():
    print("Available audio input devices:")
    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] > 0:
            print(f"  [{i}] {dev['name']}")


def resolve_mic():
    if MIC_INDEX is not None:
        return MIC_INDEX
    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] <= 0:
            continue
        name = dev['name'].lower()
        if 'monitor' in name or 'sink' in name:
            continue
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1,
                                   dtype='int16', device=i,
                                   blocksize=FRAME_SAMPLES):
                pass
            return i
        except Exception:
            continue
    return None


def has_mic():
    return resolve_mic() is not None


def record_vad_segment():
    mic = resolve_mic()
    if mic is None:
        raise RuntimeError("No usable microphone found. "
                           "Check list-devices.sh or set MIC_DEVICE_INDEX.")
    vad = webrtcvad.Vad(VAD_MODE)

    ring_buffer = collections.deque(maxlen=PADDING_FRAMES)
    pre_roll = collections.deque(maxlen=PRE_ROLL_FRAMES)

    triggered = False
    voiced_frames = []

    print("Listening... (speak now)")
    with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16',
                           device=mic, blocksize=FRAME_SAMPLES) as stream:
        while True:
            frame_bytes, _ = stream.read(FRAME_SAMPLES)
            is_speech = vad.is_speech(bytes(frame_bytes), SAMPLE_RATE)

            _debug_frames.append(frame_bytes)
            if len(_debug_frames) >= DEBUG_INTERVAL_FRAMES:
                samples = np.frombuffer(b''.join(_debug_frames), dtype=np.int16).astype(np.float32)
                rms_pct  = np.sqrt(np.mean(samples ** 2)) / 32768 * 100
                peak_pct = np.max(np.abs(samples))         / 32768 * 100
                state = "recording" if triggered else "listening"
                print(f"VAD: [{state}] volume RMS={rms_pct:.1f}%  peak={peak_pct:.1f}%")
                _debug_frames.clear()

            if not triggered:
                try:
                    event = system_events.get_nowait()
                    return None, event
                except queue.Empty:
                    pass
                pre_roll.append(frame_bytes)

            if not triggered:
                ring_buffer.append((frame_bytes, is_speech))
                num_voiced = sum(1 for _, s in ring_buffer if s)

                if num_voiced > 0.9 * ring_buffer.maxlen:
                    triggered = True
                    voiced_frames.extend(pre_roll)
                    ring_buffer.clear()
                    print(f"VAD: speech start detected - recording (pre-roll: {len(pre_roll) * FRAME_MS}ms)")
            else:
                voiced_frames.append(frame_bytes)
                ring_buffer.append((frame_bytes, is_speech))
                num_unvoiced = sum(1 for _, s in ring_buffer if not s)

                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    duration_ms = len(voiced_frames) * FRAME_MS
                    print(f"VAD: speech end detected - {duration_ms}ms of audio captured")
                    break

    audio = np.frombuffer(b''.join(voiced_frames), dtype=np.int16)
    return audio, None


def _to_wav_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    buf.seek(0)
    return buf.read()


def get_audio() -> bytes:
    """Record a VAD-gated speech segment and return it as WAV bytes."""
    if not has_mic():
        logging.warning("No microphone found, skipping audio capture")
        return b""
    audio, _ = record_vad_segment()
    if audio is None:
        return b""
    return _to_wav_bytes(audio)
