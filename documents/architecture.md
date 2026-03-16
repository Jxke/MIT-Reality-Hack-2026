# SoundSense Architecture

## Data Flow Summary

1. **MCU → bridge_shim**: The Zephyr sketch reads the 4-mic array at 8 kHz and emits `Bridge.notify("audio", pkt)` (128-sample int8 packets at ~62.5 Hz) and `Bridge.notify("direction", "front,150")` (~10 Hz). `arduino-router` reads these over UART and delivers them to `bridge_shim.py` via `arduino.app_utils`.

2. **bridge_shim → pipeline**: `bridge_shim.py` re-serves events as MsgPack-RPC TCP on port 7000. `docker-proxy` forwards host:7000 → container:7000, so `arduino_client.py` connects to `127.0.0.1:7000`.

3. **VAD → Whisper**: `arduino_client.py` feeds int8 samples into `VADBatcher`, which buffers them into 30 ms frames and runs `webrtcvad`. On speech end, it enqueues the segment as a peak-normalized WAV. `main.py` polls `get_segment()`, saves a debug clip, then POSTs the WAV to `whisper-server` over HTTP.

4. **Whisper → AR client**: Transcribed text is packed with direction data into a JSON frame (`S{…}E\n`) and broadcast over TCP to all connected Unity/AR clients via `ar_server.py` on port 9001.

5. **USB mic path** (alternative): When `USE_ARDUINO_MIC=false`, `audio.py` captures from a USB mic via `sounddevice`, runs its own VAD loop, and returns WAV bytes directly to `main.py` — bypassing `arduino_client` and `VADBatcher`.
