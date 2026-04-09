# Arduino MCU ↔ Python MPU Communication

## Architecture Overview

```
Arduino Uno Q (MCU)
    ↓ Bridge.notify()
UNO Q Linux (RouterBridge)
    ↓ TCP Port 7000
Python Backend (ElevenLabs)
    ↓ TCP Port 7000
Unity AR Client
```

---

## 1. Primary Path: Bridge.notify() → TCP Port 7000

### Arduino MCU → UNO Q Linux

**File:** `Arduino/sketch/sketch.ino`

The MCU reads 4 analog sensors and sends rising-edge events via `Bridge.notify()`.

```
Channel A0 → Sensor 1
Channel A1 → Sensor 2
Channel A2 → Sensor 3
Channel A3 → Sensor 4

Thresholds:
  LOW_TH  = 2600  (below = inactive)
  HIGH_TH = 3400  (above = active)

Debounce:   200ms minimum gap between events per channel
Averaging:  3-sample average per 10ms loop iteration
Message:    Bridge.notify("mcu_line", "1") — sensor # as string "1"-"4"
```

Signal flow:
```
MCU reads A0-A3
  → hysteresis latch
  → rising edge detection
  → Bridge.notify("mcu_line", "1-4")
```

### UNO Q Linux → TCP Clients

**File:** `Arduino/python/main.py`

- TCP server listening on `0.0.0.0:7000`
- Receives MCU events via RouterBridge, rebroadcasts to all connected TCP clients
- Bidirectional: also relays messages from clients to other clients

---

## 2. Message Framing Protocol

All TCP messages share the same frame format:

```
"S" + payload + "E\n"
```

| Direction         | Example                        |
|-------------------|--------------------------------|
| MCU → Python      | `S2E\n`                        |
| Python → Unity    | `S{"type":"caption",...}E\n`   |

**Parsing:** scan buffer for `S`...`E`, extract content between them. Handles partial frames and multiple frames in a single `recv()`.

---

## 3. Caption JSON Format (Python → Unity)

**File:** `ElevenLabs/backend/tcp_client.py`

```json
{
  "type": "caption",
  "mode": "speech",
  "text": "Hello world",
  "isFinal": true,
  "direction": 2,
  "confidence": 0.75,
  "timestamp": 1704067200.123
}
```

Sent as: `S{"type":"caption",...}E\n` (UTF-8 encoded)

A plain-text mode is also supported (`TCP_MESSAGE_FORMAT=text`), which sends only the text string as the payload.

---

## 4. Alternative Path: Serial (ESP32)

### High-Speed Audio Stream

**File:** `Arduino/bridge_mic/bridge_mic.ino`

Raw I2S audio streamed over serial, read by `ElevenLabs/backend/serial_reader.py`:

| Parameter   | Value              |
|-------------|--------------------|
| Baud rate   | 2,000,000          |
| Sample rate | 16,000 Hz          |
| Format      | PCM16 (raw binary) |
| Chunk size  | 512 samples (1024 bytes, ~32ms) |

Processing pipeline:
```
ADC (12-bit) → I2S DMA (512 samples)
  → DC offset removal
  → scaling ×16 (SPW2430 mic)
  → clip to int16 range
  → Serial.write() at 2Mbps
```

### JSON Direction/Confidence

**File:** `ElevenLabs/backend/serial_reader.py`

Alternative serial protocol at 115200 baud, one JSON object per line:

```json
{"direction": 1, "confidence": 0.95}
```

Port auto-detection searches for `/dev/cu.usbmodem*` or `/dev/cu.usbserial*`.

---

## 5. ESP32 WiFi WAV Recorder

**File:** `Arduino/Sensor Test/mictest/mictest.ino`

Serves a web interface for on-demand audio capture.

| Endpoint     | Description                        |
|--------------|------------------------------------|
| `GET /`      | HTML UI                            |
| `GET /record`| Trigger 5-second recording         |
| `GET /record.wav` | Download WAV file             |

Audio format: 11,025 Hz mono PCM16 WAV, stored on LittleFS.

---

## 6. Gating Logic

**File:** `ElevenLabs/backend/message_bus.py`

Captions are only emitted when ALL criteria pass:

| Condition              | Threshold                          |
|------------------------|------------------------------------|
| Direction stable for   | ≥ 400ms (`DIRECTION_STABLE_MS`)    |
| Direction confidence   | ≥ 0.20 (`MIN_CONFIDENCE`)          |
| Audio RMS energy       | ≥ 0.00002 (`MIN_ENERGY`)           |

VAD thresholds (from `ElevenLabs/backend/config.py`):

```python
VAD_START_THRESHOLD = 0.02   # begin buffering speech
VAD_STOP_THRESHOLD  = 0.01   # end speech segment
MAX_SPEECH_SECONDS  = 8.0    # max buffer duration
```

---

## 7. Full Data Flow

```
Arduino Uno Q
  reads A0-A3 @ 10ms → hysteresis → rising edge → debounce 200ms
  └─ Bridge.notify("mcu_line", "2")

UNO Q Linux (RouterBridge)
  └─ TCP server :7000 → rebroadcasts "S2E\n" to all clients

Python Backend
  ├─ receives "S2E\n" → direction = 2
  ├─ captures audio (USB mic, 16kHz, 0.5s chunks)
  ├─ VAD → speech segment → STT (ElevenLabs / Whisper.cpp)
  ├─ gating: direction stable 400ms + conf ≥ 0.20 + energy ≥ 0.00002
  └─ sends "S{json}E\n" to TCP server

Unity AR Client
  └─ receives caption JSON → renders in AR
```

---

## 8. Key Files

| File | Role |
|------|------|
| `Arduino/sketch/sketch.ino` | MCU firmware — sensor reading, Bridge.notify |
| `Arduino/python/main.py` | RouterBridge TCP server (port 7000) |
| `Arduino/bridge_mic/bridge_mic.ino` | ESP32 I2S → serial audio stream |
| `Arduino/Sensor Test/mictest/mictest.ino` | ESP32 WiFi WAV recorder |
| `ElevenLabs/backend/main.py` | Python orchestrator |
| `ElevenLabs/backend/tcp_client.py` | TCP client + message framing |
| `ElevenLabs/backend/serial_reader.py` | Serial reader (audio + JSON) |
| `ElevenLabs/backend/message_bus.py` | Gating logic + state tracking |
| `ElevenLabs/backend/audio_stream.py` | USB mic capture |
| `ElevenLabs/backend/config.py` | All configuration parameters |
