# SoundSight - AR Caption System

Real-time audio captioning system that combines Arduino direction sensing, USB microphone capture, speech-to-text, and sound event classification for AR applications.

## Architecture

- **Arduino**: Reads 4 analog amplitude sensors (A0-A3), computes loudest direction + confidence, streams JSON over Serial USB
- **UNO Q TCP Server**: Accepts TCP clients, rebroadcasts sensor + caption frames to all clients
- **Python Backend (ElevenLabs)**: Captures audio, performs VAD, transcribes speech (ElevenLabs API), applies gating logic, connects as a TCP client to UNO Q and sends captions
- **Unity Client**: Connects to UNO Q TCP server and receives frames via TCP

## Setup

### Prerequisites

- macOS (tested on macOS 14+)
- Python 3.10 or higher
- Arduino IDE (for uploading firmware)
- Unity 2021.3+ (for AR client)

### 1. Python Backend Setup

```bash
# Navigate to project directory
cd ./ElevenLabs

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: The backend uses ElevenLabs Speech-to-Text API. You'll need to set your API key (see below).

### 2. Arduino Setup

1. Connect Arduino to Mac via USB
2. Open `arduino/loudest_direction.ino` in Arduino IDE
3. Select your board (Arduino Uno/Nano/etc.)
4. Upload sketch
5. Open Serial Monitor at 115200 baud to verify JSON output

**Hardware**: Connect 4 analog sensors (microphones/amplitude sensors) to pins A0, A1, A2, A3.

### 3. Finding Serial Port on macOS

The backend auto-detects serial ports, but you can manually specify:

```bash
# List available serial ports
ls /dev/cu.*

# Common Arduino ports:
# /dev/cu.usbmodem14101 (Arduino Uno)
# /dev/cu.usbserial-* (FTDI/other adapters)

# Set manually via environment variable:
export SERIAL_PORT=/dev/cu.usbmodem14101
```

### 4. ElevenLabs API Key Setup

The backend uses ElevenLabs batch Speech-to-Text API. You must set your API key before running:

```bash
# Set API key (replace with your actual key)
export ELEVENLABS_API_KEY=""

# Verify it's set
echo $ELEVENLABS_API_KEY
```

**Important**: 
- Keep your API key secure and never commit it to version control
- The key must stay server-side (backend only)
- ElevenLabs provides both batch and realtime STT APIs; we use batch for hackathon segmentation

Get your API key from: https://elevenlabs.io/app/settings/api-keys

### 5. Microphone Permissions

macOS requires microphone permissions:

1. System Settings > Privacy & Security > Microphone
2. Enable Terminal (or your Python IDE) to access microphone
3. Restart terminal/IDE after granting permissions

To test microphone access:
```python
import sounddevice as sd
print(sd.query_devices())  # Should list available devices
```

### 6. Running the Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Run backend
cd backend
python main.py
```

The backend will:
- Auto-detect Arduino serial port (set `ENABLE_SERIAL=0` to skip)
- Start audio capture from default microphone
- Connect to ElevenLabs API for speech transcription
- Connect to UNO Q TCP server at `tcp://<UNO_Q_IP>:7000`

**Note**: Make sure `ELEVENLABS_API_KEY` is set before running, or the backend will fail to initialize.

### 7. Start the UNO Q TCP Server

On the UNO Q (Linux side), start the TCP server so it can rebroadcast to Unity:

```bash
python /home/arduino/Arduino/python/main.py
```

You should see:
```
TCP server listening on port 7000
```

### 8. Unity Client Setup

1. Open Unity project
2. Add your TCP receiver script to a GameObject in your scene
3. Configure TCP host/port to the UNO Q IP (e.g. `10.29.193.69:7000`)
4. Run scene - captions will appear in console (implement UI display as needed)

**Important**: Parse frames as `S...E\n` (end marker is the literal `E\n`, not any single `E`).

## Configuration

Edit `backend/config.py` to adjust thresholds:

```python
# VAD thresholds (RMS energy)
VAD_START_THRESHOLD = 0.02  # Start detecting speech
VAD_STOP_THRESHOLD = 0.01   # Stop detecting speech
VAD_HANGOVER_BLOCKS = 3     # Blocks to wait after energy drops

# Direction gating
DIRECTION_STABLE_MS = 400    # Direction must be stable (ms)
MIN_CONFIDENCE = 0.20        # Minimum confidence (0.0-1.0)
MIN_ENERGY = 0.015           # Minimum RMS energy

# Speech-to-Text (ElevenLabs)
# API key must be set via ELEVENLABS_API_KEY environment variable
```

### Environment Variables

```bash
# Serial port (auto-detected if not set)
export SERIAL_PORT=/dev/cu.usbmodem14101
export ENABLE_SERIAL=1  # Set to 0 to disable direction gating

# ElevenLabs API key (required)
export ELEVENLABS_API_KEY="your_api_key_here"

# TCP server (UNO Q)
export TCP_HOST=10.29.193.69
export TCP_PORT=7000
export TCP_MESSAGE_FORMAT=text  # text or json

# Optional gating/timing
export ENABLE_GATING=1
export MAX_SPEECH_SECONDS=8
export MIN_ENERGY=0.002

# Optional debug audio capture
export SAVE_AUDIO_DIR=./debug_audio
export SAVE_AUDIO_MAX=5

# Optional audio device selection
export AUDIO_DEVICE_INDEX=0
export AUDIO_USE_DEVICE_DEFAULT=1

# Logging
export LOG_LEVEL=DEBUG
```

### Quick Start (recommended)

Use a local `.env` (ignored by git) and load it before running:

```bash
set -a; source ElevenLabs/.env; set +a
python3 ElevenLabs/backend/main.py
```

## Testing

### Test Serial Connection

```bash
# Monitor serial output
screen /dev/cu.usbmodem14101 115200

# Or use Python
python -c "from backend.serial_reader import SerialReader; r = SerialReader(); r.connect(); print(r.read_line())"
```

### Test TCP Server (UNO Q)

```python
# Test TCP connection (from another terminal, or your Unity client)
import socket

def test():
    host = "10.29.193.69"
    port = 7000
    sock = socket.create_connection((host, port))
    print(f"Connected to {host}:{port}")
    while True:
        data = sock.recv(4096)
        if not data:
            break
        print(data.decode("utf-8").strip())

test()
```

Or run:
```bash
python test_tcp_client.py
```

### Test Unity Client

1. Run backend
2. Run Unity scene with your TCP receiver component
3. Speak into microphone or generate sounds
4. Check Unity console for caption events

## Message Format

Caption events sent via TCP (framed as `S...E`). Set `TCP_MESSAGE_FORMAT=json` to send full JSON, or `text` to send just the caption text.

```json
{
  "type": "caption",
  "mode": "speech",  // or "sound"
  "text": "Hello world",
  "isFinal": true,
  "direction": 2,    // 0-3 (sensor index)
  "confidence": 0.75,  // 0.0-1.0
  "timestamp": 1704067200.123
}
```

## Troubleshooting

### Serial Port Not Found

- Check Arduino is connected and drivers installed
- Verify port appears in `/dev/cu.*`
- Try setting `SERIAL_PORT` environment variable explicitly

### Microphone Not Working

- Grant microphone permissions in System Settings
- Check default input device: `python -c "import sounddevice as sd; print(sd.default.device)"`
- List devices: `python -c "import sounddevice as sd; sd.query_devices()"`

### ElevenLabs API Errors

- Verify API key is set: `echo $ELEVENLABS_API_KEY`
- Check API key is valid at https://elevenlabs.io/app/settings/api-keys
- Review API usage limits and billing
- Check network connectivity to api.elevenlabs.io

### TCP Connection Refused

- Verify your TCP server is running on `:7000`
- Check firewall settings
- Try different port: `export TCP_PORT=7001`

### No Captions Appearing

- Check VAD thresholds (may be too high/low)
- Verify direction gating: direction stable >= 400ms, confidence >= 0.20
- Check audio energy: `MIN_ENERGY` threshold
- Enable debug logging: `export LOG_LEVEL=DEBUG`
- Ensure Unity parses the frame terminator `E\n` (not any single `E`)

## MediaPipe Integration (TODO)

The sound classifier currently uses placeholder logic. To fully implement MediaPipe:

1. Install MediaPipe:
   ```bash
   pip install mediapipe
   ```

2. Download Audio Classifier model:
   - Visit: https://ai.google.dev/edge/mediapipe/solutions/audio/audio_classifier
   - Download YAMNet or custom TFLite model
   - Place in `models/` directory

3. Update `backend/classifier_mediapipe.py`:
   - Uncomment MediaPipe initialization code
   - Update `classify()` method to use actual classifier
   - Handle model-specific input requirements

See `backend/classifier_mediapipe.py` for detailed TODO comments.

## Project Structure

```
ElevenLabs/
├── backend/
│   ├── main.py                    # Main orchestrator
│   ├── config.py                  # Configuration
│   ├── serial_reader.py          # Arduino serial interface
│   ├── audio_stream.py            # Microphone capture
│   ├── vad.py                     # Voice Activity Detection
│   ├── stt_whisper.py             # Speech-to-Text
│   ├── classifier_mediapipe.py    # Sound classification
│   ├── tcp_client.py               # TCP client
│   └── message_bus.py             # Message coordination
├── Arduino/python/
│   └── main.py                     # UNO Q TCP server + rebroadcast
├── unity/
│   └── (your TCP receiver script)  # Unity TCP client (S...E\n framing)
├── requirements.txt
└── README.md
```

## License

MIT License - Hackathon project

## Credits

- faster-whisper: https://github.com/guillaumekln/faster-whisper
- MediaPipe: https://ai.google.dev/edge/mediapipe
