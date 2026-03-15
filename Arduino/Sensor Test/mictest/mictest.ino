#include <WiFi.h>
#include <WebServer.h>
#include <FS.h>
#include <LittleFS.h>
#include <math.h>

// =========================
// WiFi
// =========================
const char* WIFI_SSID = "Tim Apple iPhone";
const char* WIFI_PASS = "thesameasyours";

// =========================
// Audio config
// =========================
static const int MIC_PIN = 34;          // ADC1 pin
static const int SAMPLE_RATE = 11025;   // decent for voice tests
static const int RECORD_SECONDS = 5;
static const int ADC_BITS = 12;

WebServer server(80);

// Filtering state
float dcEstimate = 2048.0f;
float smoothSample = 0.0f;

// =========================
// Simple page
// =========================
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>ESP32 WAV Recorder</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; }
    button { font-size: 16px; padding: 10px 16px; margin-right: 8px; margin-bottom: 12px; }
    .mono { font-family: monospace; white-space: pre-wrap; }
    audio { width: 100%; margin-top: 16px; }
  </style>
</head>
<body>
  <h1>ESP32 WAV Recorder</h1>
  <p>Press record, wait 5 seconds, then play or download the file.</p>

  <button id="recordBtn">Record 5s</button>
  <button id="refreshBtn">Refresh Player</button>

  <p class="mono" id="status">Idle</p>

  <audio id="player" controls></audio>
  <p><a id="downloadLink" href="/record.wav" download="record.wav">Download WAV</a></p>

  <script>
    const statusEl = document.getElementById("status");
    const player = document.getElementById("player");

    async function recordClip() {
      statusEl.textContent = "Recording... please wait about 5 seconds.";
      const res = await fetch("/record", { cache: "no-store" });
      const text = await res.text();
      statusEl.textContent = text;
      refreshPlayer();
    }

    function refreshPlayer() {
      const url = "/record.wav?t=" + Date.now();
      player.src = url;
      player.load();
      document.getElementById("downloadLink").href = url;
      statusEl.textContent = "Player refreshed.";
    }

    document.getElementById("recordBtn").addEventListener("click", recordClip);
    document.getElementById("refreshBtn").addEventListener("click", refreshPlayer);

    refreshPlayer();
  </script>
</body>
</html>
)rawliteral";

// =========================
// WAV helpers
// =========================
void writeWavHeader(File &file, uint32_t sampleRate, uint32_t dataSize) {
  uint16_t audioFormat = 1;   // PCM
  uint16_t numChannels = 1;   // mono
  uint16_t bitsPerSample = 16;
  uint32_t byteRate = sampleRate * numChannels * bitsPerSample / 8;
  uint16_t blockAlign = numChannels * bitsPerSample / 8;
  uint32_t chunkSize = 36 + dataSize;

  file.seek(0);
  file.write((const uint8_t*)"RIFF", 4);
  file.write((uint8_t*)&chunkSize, 4);
  file.write((const uint8_t*)"WAVE", 4);

  file.write((const uint8_t*)"fmt ", 4);
  uint32_t subchunk1Size = 16;
  file.write((uint8_t*)&subchunk1Size, 4);
  file.write((uint8_t*)&audioFormat, 2);
  file.write((uint8_t*)&numChannels, 2);
  file.write((uint8_t*)&sampleRate, 4);
  file.write((uint8_t*)&byteRate, 4);
  file.write((uint8_t*)&blockAlign, 2);
  file.write((uint8_t*)&bitsPerSample, 2);

  file.write((const uint8_t*)"data", 4);
  file.write((uint8_t*)&dataSize, 4);
}

// =========================
// Mic sample + filter
// =========================
int16_t readFilteredSample() {
  int raw = analogRead(MIC_PIN);

  // Slightly faster DC tracking
  dcEstimate = 0.995f * dcEstimate + 0.005f * raw;
  float centered = raw - dcEstimate;

  // Stronger noise gate
  if (fabs(centered) < 12.0f) centered = 0.0f;

  // Less smoothing so it sounds less muffled
  smoothSample = 0.65f * smoothSample + 0.35f * centered;

  // Slightly lower scaling to avoid bringing noise back up too much
  float s = smoothSample * 10.0f;

  if (s > 32767.0f) s = 32767.0f;
  if (s < -32768.0f) s = -32768.0f;

  return (int16_t)s;
}

// =========================
// Record function
// =========================
bool recordWav(const char* path, int seconds) {
  if (LittleFS.exists(path)) {
    LittleFS.remove(path);
  }

  File file = LittleFS.open(path, FILE_WRITE);
  if (!file) return false;

  // placeholder header
  uint8_t emptyHeader[44] = {0};
  file.write(emptyHeader, 44);

  const uint32_t totalSamples = SAMPLE_RATE * seconds;
  const uint32_t usPerSample = 1000000UL / SAMPLE_RATE;
  uint32_t nextMicros = micros();

  uint32_t bytesWritten = 0;

  // reset filter state at start of each take
  dcEstimate = 2048.0f;
  smoothSample = 0.0f;

  for (uint32_t i = 0; i < totalSamples; i++) {
    while ((int32_t)(micros() - nextMicros) < 0) {
      // wait
    }
    nextMicros += usPerSample;

    int16_t sample = readFilteredSample();
    file.write((uint8_t*)&sample, sizeof(sample));
    bytesWritten += sizeof(sample);
  }

  writeWavHeader(file, SAMPLE_RATE, bytesWritten);
  file.close();
  return true;
}

// =========================
// Routes
// =========================
void handleRoot() {
  server.send_P(200, "text/html", INDEX_HTML);
}

void handleRecord() {
  server.sendHeader("Connection", "close");

  bool ok = recordWav("/record.wav", RECORD_SECONDS);
  if (ok) {
    server.send(200, "text/plain", "Done. Recorded 5 seconds to /record.wav");
  } else {
    server.send(500, "text/plain", "Failed to record file.");
  }
}

void handleWav() {
  if (!LittleFS.exists("/record.wav")) {
    server.send(404, "text/plain", "No recording yet.");
    return;
  }

  File file = LittleFS.open("/record.wav", FILE_READ);
  if (!file) {
    server.send(500, "text/plain", "Could not open WAV file.");
    return;
  }

  server.streamFile(file, "audio/wav");
  file.close();
}

void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

// =========================
// Setup
// =========================
void setup() {
  Serial.begin(115200);
  delay(500);

  // ADC setup
  analogReadResolution(ADC_BITS);
  analogSetPinAttenuation(MIC_PIN, ADC_11db);

  // File system
  if (!LittleFS.begin(true)) {
    Serial.println("LittleFS mount failed");
    while (true) delay(1000);
  }

  // WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected. IP: ");
  Serial.println(WiFi.localIP());

  // Web server
  server.on("/", handleRoot);
  server.on("/record", HTTP_GET, handleRecord);
  server.on("/record.wav", HTTP_GET, handleWav);
  server.onNotFound(handleNotFound);
  server.begin();

  Serial.println("Open in browser:");
  Serial.print("http://");
  Serial.println(WiFi.localIP());
}

void loop() {
  server.handleClient();
}