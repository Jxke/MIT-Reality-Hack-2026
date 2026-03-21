#!/usr/bin/env python3
"""mic-monitor — stream MCU microphone audio to a browser.

Does NOT use arduino.app_utils directly.  Instead it connects to the
already-running bridge-shim on localhost:7000 as a second TCP client,
reads MsgPack-RPC notifications ([2, "audio", [samples]]), and forwards
them over WebSocket to any browser that opens the web UI.

Usage (from the Arduino UNO Q Linux MPU):
  python3 ~/ArduinoApps/mic-monitor/python/main.py

Open in browser:
  http://<board-ip>:8082/
"""

import base64
import hashlib
import socket
import struct
import threading
import time

import msgpack

BRIDGE_HOST  = "127.0.0.1"
BRIDGE_PORT  = 7000          # bridge-shim TCP port
WEB_PORT     = 8082
SAMPLE_RATE  = 8000          # must match sketch #define SAMPLE_RATE
RECONNECT_S  = 3             # seconds between bridge reconnect attempts

# ── WebSocket client registry ──────────────────────────────────────────────

_ws_clients: list = []
_ws_lock = threading.Lock()

_WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _ws_frame(data: bytes) -> bytes:
    n = len(data)
    if n < 126:
        hdr = struct.pack('BB', 0x82, n)
    elif n < 65536:
        hdr = struct.pack('!BBH', 0x82, 126, n)
    else:
        hdr = struct.pack('!BBQ', 0x82, 127, n)
    return hdr + data


def _broadcast(data: bytes) -> None:
    frame = _ws_frame(data)
    with _ws_lock:
        dead = []
        for sock in _ws_clients:
            try:
                sock.sendall(frame)
            except OSError:
                dead.append(sock)
        for s in dead:
            _ws_clients.remove(s)
            try:
                s.close()
            except OSError:
                pass


# ── Bridge-shim TCP client ─────────────────────────────────────────────────

def _bridge_loop() -> None:
    """Connect to bridge-shim:7000 and forward audio packets indefinitely."""
    while True:
        try:
            sock = socket.create_connection((BRIDGE_HOST, BRIDGE_PORT), timeout=5)
            print(f"[bridge] connected to {BRIDGE_HOST}:{BRIDGE_PORT}", flush=True)
            unpacker = msgpack.Unpacker(raw=False)
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                unpacker.feed(chunk)
                for msg in unpacker:
                    # MsgPack-RPC notification: [2, topic, payload]
                    if not (isinstance(msg, (list, tuple)) and len(msg) == 3):
                        continue
                    msg_type, topic, payload = msg
                    if msg_type != 2 or topic != "audio":
                        continue
                    # payload is list[int] (signed int8 samples)
                    _broadcast(bytes(s & 0xFF for s in payload))
        except (OSError, msgpack.UnpackException) as exc:
            print(f"[bridge] disconnected ({exc}), retrying in {RECONNECT_S}s…", flush=True)
        finally:
            try:
                sock.close()
            except Exception:
                pass
        time.sleep(RECONNECT_S)


threading.Thread(target=_bridge_loop, daemon=True, name="bridge-client").start()

# ── HTML page ──────────────────────────────────────────────────────────────

_INDEX_HTML = f"""\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MCU Mic Monitor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body  {{ font-family: sans-serif; max-width: 640px; margin: 60px auto; padding: 0 16px; }}
    h1    {{ margin-bottom: 4px; }}
    .sub  {{ color: #666; margin-top: 0; font-size: 14px; }}
    button {{ font-size: 15px; padding: 10px 20px; margin: 6px 4px; cursor: pointer; }}
    button:disabled {{ opacity: .45; cursor: default; }}
    #status {{ margin-top: 20px; font-family: monospace;
               display: flex; align-items: center; gap: 10px; }}
    .dot  {{ width: 11px; height: 11px; border-radius: 50%; background: #bbb; flex-shrink: 0; }}
    .dot.live {{ background: #3c3; animation: pulse 1.2s infinite; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.35}} }}
    canvas {{ display: block; margin-top: 24px; width: 100%; border-radius: 6px;
              background: #111; }}
    #scope {{ height: 80px; }}
    #freq  {{ height: 120px; margin-top: 8px; }}
    .freq-labels {{ display: flex; justify-content: space-between;
                    font-size: 11px; color: #666; font-family: monospace;
                    margin: 2px 0 0; padding: 0; }}
  </style>
</head>
<body>
  <h1>MCU Mic Monitor</h1>
  <p class="sub">Signed 8-bit PCM &bull; {SAMPLE_RATE}&thinsp;Hz &bull; mono (A0&#8239;+&#8239;A3 mix)</p>

  <button id="startBtn">&#9654; Start Listening</button>
  <button id="stopBtn" disabled>&#9646;&#9646; Stop</button>

  <div id="status"><span class="dot" id="dot"></span><span id="txt">Idle</span></div>
  <canvas id="scope" width="640" height="80"></canvas>
  <canvas id="freq"  width="640" height="120"></canvas>
  <div class="freq-labels">
    <span>0 Hz</span><span>500</span><span>1k</span><span>2k</span><span>4k</span>
  </div>

  <script>
  (function () {{
    const RATE     = {SAMPLE_RATE};
    const PREBUF   = 0.10;
    const canvas   = document.getElementById('scope');
    const ctx2d    = canvas.getContext('2d');
    const fCanvas  = document.getElementById('freq');
    const fCtx     = fCanvas.getContext('2d');
    const dot      = document.getElementById('dot');
    const txt      = document.getElementById('txt');
    const startBtn = document.getElementById('startBtn');
    const stopBtn  = document.getElementById('stopBtn');

    let audioCtx = null, ws = null, nextPlayTime = 0;
    let analyser = null, rafId = null;
    const scopeBuf = new Float32Array(canvas.width);

    // ── frequency display ───────────────────────────────────────────
    const FFT_SIZE = 1024;  // → 512 bins, 0–4000 Hz at 8 kHz

    function drawFreq() {{
      rafId = requestAnimationFrame(drawFreq);
      if (!analyser) return;

      const bins = new Uint8Array(analyser.frequencyBinCount); // 512
      analyser.getByteFrequencyData(bins);

      const W = fCanvas.width, H = fCanvas.height;
      fCtx.clearRect(0, 0, W, H);

      const barW = W / bins.length;
      for (let i = 0; i < bins.length; i++) {{
        const v   = bins[i];                        // 0–255
        const pct = v / 255;
        const h   = pct * H;
        // green → yellow → red as amplitude rises
        fCtx.fillStyle = `hsl(${{120 - pct * 120}}, 90%, 45%)`;
        fCtx.fillRect(i * barW, H - h, Math.ceil(barW), h);
      }}

      // frequency tick lines at 500 / 1k / 2k Hz
      fCtx.strokeStyle = 'rgba(255,255,255,0.15)';
      fCtx.lineWidth   = 1;
      for (const hz of [500, 1000, 2000]) {{
        const x = Math.round(hz * FFT_SIZE / RATE * W / (FFT_SIZE / 2));
        fCtx.beginPath(); fCtx.moveTo(x, 0); fCtx.lineTo(x, H); fCtx.stroke();
      }}
    }}

    function setStatus(msg, live) {{
      txt.textContent = msg;
      dot.className   = 'dot' + (live ? ' live' : '');
    }}

    // Samples displayed across the full canvas width (controls scroll speed)
    const SAMPLES_PER_PIX = Math.max(1, Math.round(RATE / canvas.width));

    function drawScope(f32) {{
      // How many pixels does this packet advance the scope?
      const pixCount = Math.max(1, Math.ceil(f32.length / SAMPLES_PER_PIX));
      // Scroll existing content left
      scopeBuf.copyWithin(0, pixCount);
      // Fill the rightmost pixCount pixels with peak values from this packet
      for (let p = 0; p < pixCount; p++) {{
        const start = Math.floor(p * f32.length / pixCount);
        const end   = Math.floor((p + 1) * f32.length / pixCount);
        let peak = 0;
        for (let i = start; i < end; i++) {{
          const v = Math.abs(f32[i] || 0);
          if (v > peak) peak = v;
        }}
        scopeBuf[canvas.width - pixCount + p] = peak;
      }}

      ctx2d.clearRect(0, 0, canvas.width, canvas.height);
      ctx2d.strokeStyle = '#3f3';
      ctx2d.lineWidth   = 1;
      ctx2d.beginPath();
      const mid = canvas.height / 2;
      for (let x = 0; x < canvas.width; x++) {{
        const y = mid - scopeBuf[x] * mid;
        x === 0 ? ctx2d.moveTo(x, y) : ctx2d.lineTo(x, y);
      }}
      ctx2d.stroke();
    }}

    function handlePacket(buf) {{
      const int8 = new Int8Array(buf);
      const f32  = new Float32Array(int8.length);
      for (let i = 0; i < int8.length; i++) f32[i] = int8[i] / 128.0;

      const abuf = audioCtx.createBuffer(1, f32.length, RATE);
      abuf.copyToChannel(f32, 0);
      const src = audioCtx.createBufferSource();
      src.buffer = abuf;
      src.connect(analyser);
      analyser.connect(audioCtx.destination);

      const now = audioCtx.currentTime;
      if (nextPlayTime < now + 0.01) nextPlayTime = now + PREBUF;
      src.start(nextPlayTime);
      nextPlayTime += f32.length / RATE;

      drawScope(f32);
    }}

    startBtn.addEventListener('click', () => {{
      if (ws) return;
      audioCtx     = new (window.AudioContext || window.webkitAudioContext)({{ sampleRate: RATE }});
      nextPlayTime = audioCtx.currentTime + PREBUF;
      analyser          = audioCtx.createAnalyser();
      analyser.fftSize  = FFT_SIZE;
      analyser.smoothingTimeConstant = 0.75;
      drawFreq();

      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(proto + '//' + location.host + '/ws');
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {{
        setStatus('Connected — listening…', true);
        startBtn.disabled = true;
        stopBtn.disabled  = false;
      }};

      ws.onclose = ws.onerror = () => {{
        setStatus('Disconnected', false);
        startBtn.disabled = false;
        stopBtn.disabled  = true;
        ws = null;
      }};

      ws.onmessage = (ev) => handlePacket(ev.data);
    }});

    stopBtn.addEventListener('click', () => {{
      if (rafId)    {{ cancelAnimationFrame(rafId); rafId = null; }}
      if (ws)       {{ ws.close();       ws = null; }}
      if (audioCtx) {{ audioCtx.close(); audioCtx = null; }}
      analyser = null;
      fCtx.clearRect(0, 0, fCanvas.width, fCanvas.height);
      startBtn.disabled = false;
      stopBtn.disabled  = true;
      setStatus('Stopped', false);
    }});
  }})();
  </script>
</body>
</html>
"""

# ── HTTP + WebSocket handler ───────────────────────────────────────────────

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # noqa: N802
        print(f"[http] {self.address_string()} — {fmt % args}", flush=True)

    def do_GET(self):  # noqa: N802
        if self.path in ('/', '/index.html'):
            body = _INDEX_HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == '/ws':
            key    = self.headers.get('Sec-WebSocket-Key', '')
            accept = base64.b64encode(
                hashlib.sha1((key + _WS_MAGIC).encode()).digest()
            ).decode()
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept)
            self.end_headers()
            self.wfile.flush()

            conn = self.connection
            with _ws_lock:
                _ws_clients.append(conn)
            print(f"[ws] connected: {self.client_address}", flush=True)

            try:
                while True:
                    hdr = conn.recv(2)
                    if len(hdr) < 2:
                        break
                    opcode = hdr[0] & 0x0F
                    length = hdr[1] & 0x7F
                    if length == 126:
                        length = struct.unpack('!H', conn.recv(2))[0]
                    elif length == 127:
                        length = struct.unpack('!Q', conn.recv(8))[0]
                    masked  = bool(hdr[1] & 0x80)
                    mask    = conn.recv(4) if masked else b'\x00\x00\x00\x00'
                    payload = bytearray(conn.recv(length))
                    if masked:
                        for i in range(len(payload)):
                            payload[i] ^= mask[i % 4]
                    if opcode == 0x9:   # ping → pong
                        conn.sendall(struct.pack('BB', 0x8A, len(payload)) + bytes(payload))
                    elif opcode == 0x8: # close
                        break
            except OSError:
                pass
            finally:
                with _ws_lock:
                    if conn in _ws_clients:
                        _ws_clients.remove(conn)
                print(f"[ws] disconnected: {self.client_address}", flush=True)

        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = _Server(('0.0.0.0', WEB_PORT), _Handler)
    print(f"[mic-monitor] http://0.0.0.0:{WEB_PORT}/", flush=True)
    print(f"[mic-monitor] bridging from {BRIDGE_HOST}:{BRIDGE_PORT}", flush=True)
    server.serve_forever()
