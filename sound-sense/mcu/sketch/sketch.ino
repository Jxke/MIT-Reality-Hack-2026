#include <Arduino_RouterBridge.h>

// =================================================================
// 4-Mic Direction Detector + Voice Audio Streamer
// Arduino UNO Q — Zephyr RTOS
//
// Microphone layout (worn as necklace, wearer facing 12 o'clock):
//   A0 = 2 o'clock  (front-right) — voice mic, low-pass filtered + streamed
//   A1 = 5 o'clock  (right)       — direction detection only
//   A2 = 7 o'clock  (left)        — direction detection only
//   A3 = 11 o'clock (front-left)  — voice mic, low-pass filtered + streamed
//
// Bridge output (to Debian pipeline via Arduino Router):
//
//   notify("audio", MsgPack::arr_t<int8_t>)
//     Signed 8-bit PCM, mono, SAMPLE_RATE Hz
//     Averaged mix of filtered A0 + A3 (voice mics)
//     Python side: np.array(pkt, dtype=np.int8) gives raw samples
//
//   notify("direction", "<dir>,<vol>")
//     <dir>: front | back | left | right
//     <vol>: peak raw amplitude 0-2048 (12-bit ADC DC-removed)
//     Schema upgrade from previous sketch's 1-4 event numbers
//
// Direction quadrant logic (pair-based):
//   front = A0 (2h) + A3 (11h)  both face forward
//   back  = A1 (5h) + A2 ( 7h)  both face backward
//   right = A0 (2h) + A1 ( 5h)  both on right side
//   left  = A3(11h) + A2 ( 7h)  both on left side
// =================================================================

// ---- Audio streaming config ----
#define SAMPLE_RATE    8000    // Hz — voice quality for Whisper
#define AUDIO_BUFSIZE  128     // samples per Bridge.notify packet (~16ms)
#define US_PER_SAMPLE  (1000000UL / SAMPLE_RATE)

// ---- Direction detection config ----
#define DIR_WINDOW     40      // samples averaged per direction window (~5ms)
#define ACTIVE_AMP_TH  30      // min average amplitude to report (0-2048 scale)
#define DIR_COOLDOWN   150UL   // ms between direction event sends

// ---- Voice filter state: A0=idx0, A3=idx1 ----
// Matches mictest.ino DC-removal + noise-gate + low-pass for 12-bit ADC
static float dcEst[2]    = { 2048.0f, 2048.0f };
static float smoothed[2] = { 0.0f,    0.0f    };

// ---- Direction tracking ----
static long     ampSum[4]  = {0, 0, 0, 0};
static int      dirCount   = 0;
static char     lastDir[8] = "none";
static uint32_t lastDirMs  = 0;

// ---- Audio buffer + timing ----
static int8_t   audioBuf[AUDIO_BUFSIZE];
static int      audioBufIdx  = 0;
static uint32_t nextSampleUs = 0;

// =================================================================
// voiceFilter — DC removal + noise gate + low-pass
// Ported from mictest.ino, adapted for 12-bit ADC (0-4095).
// idx: 0 = A0, 1 = A3
// =================================================================
static int16_t voiceFilter(int idx, int raw) {
    // Slow DC tracking (~200 sample time constant)
    dcEst[idx]     = 0.995f * dcEst[idx] + 0.005f * (float)raw;
    float centered = (float)raw - dcEst[idx];

    // Noise gate — suppress sub-threshold chatter
    if (fabsf(centered) < 3.0f) centered = 0.0f;

    // Low-pass smoothing — preserve voice, attenuate HF noise
    smoothed[idx]  = 0.10f * smoothed[idx] + 0.90f * centered;

    // 10x gain + int16 saturation (matches mictest.ino scaling)
    float s = smoothed[idx] * 60.0f;
    if (s >  32767.0f) s =  32767.0f;
    if (s < -32768.0f) s = -32768.0f;
    return (int16_t)s;
}

// =================================================================
// detectDirection — quadrant pair comparison
// All amplitudes are raw DC-removed (rawAx - 2048) for fair comparison.
// =================================================================
static const char* detectDirection(long a0, long a1, long a2, long a3) {
    long peak = max(max(a0, a1), max(a2, a3));
    if (peak < ACTIVE_AMP_TH) return "none";

    long front = a0 + a3;   // 2 + 11 o'clock
    long back  = a1 + a2;   // 5 +  7 o'clock
    long right = a0 + a1;   // 2 +  5 o'clock
    long left  = a3 + a2;   //11 +  7 o'clock
    long mx    = max(max(front, back), max(right, left));

    if (front == mx) return "front";
    if (back  == mx) return "back";
    if (right == mx) return "right";
    return "left";
}

// =================================================================
void setup() {
    Bridge.begin();      // keep the proven order
    Monitor.begin();
    delay(200);

    analogReadResolution(12);   // 0-4095, DC center ~2048

    delay(5000);  // give Linux/Python time to start
    Monitor.println("MCU ready | 4-mic | A0+A3 voice stream | direction");
}

// =================================================================
// Main loop — sample all 4 mics at SAMPLE_RATE Hz
// =================================================================
void loop() {
    uint32_t now = micros();
    if ((int32_t)(now - nextSampleUs) < 0) return;
    nextSampleUs += US_PER_SAMPLE;

    // Read all 4 electret mics
    int rawA0 = analogRead(A0);
    int rawA1 = analogRead(A1);
    int rawA2 = analogRead(A2);
    int rawA3 = analogRead(A3);

    // Single mic: A0 (2 o'clock, front-right voice mic)
    int16_t filtA0 = voiceFilter(0, rawA0);
    audioBuf[audioBufIdx++] = (int8_t)(filtA0 >> 8);

    // Flush audio packet to Debian when buffer is full
    if (audioBufIdx >= AUDIO_BUFSIZE) {
        audioBufIdx = 0;
        MsgPack::arr_t<int8_t> pkt;
        for (int i = 0; i < AUDIO_BUFSIZE; i++) pkt.push_back(audioBuf[i]);
        Bridge.notify("audio", pkt);
        Monitor.println("Audio packet sent");
    }

    // Accumulate raw DC-removed amplitudes for direction detection.
    // Use unfiltered values for all 4 mics so they are comparable.
    ampSum[0] += (long)abs(rawA0 - 2048);
    ampSum[1] += (long)abs(rawA1 - 2048);
    ampSum[2] += (long)abs(rawA2 - 2048);
    ampSum[3] += (long)abs(rawA3 - 2048);
    dirCount++;

    if (dirCount >= DIR_WINDOW) {
        long a0 = ampSum[0] / dirCount;
        long a1 = ampSum[1] / dirCount;
        long a2 = ampSum[2] / dirCount;
        long a3 = ampSum[3] / dirCount;
        memset(ampSum, 0, sizeof(ampSum));
        dirCount = 0;

        const char* dir = detectDirection(a0, a1, a2, a3);
        uint32_t nowMs  = millis();

        // Send on direction change or after cooldown (prevents flood)
        if (strcmp(dir, "none") != 0 &&
            (strcmp(dir, lastDir) != 0 || (nowMs - lastDirMs) > DIR_COOLDOWN)) {
            lastDirMs = nowMs;
            strncpy(lastDir, dir, sizeof(lastDir) - 1);
            lastDir[sizeof(lastDir) - 1] = '\0';

            long vol = max(max(a0, a1), max(a2, a3));
            char msg[24];
            snprintf(msg, sizeof(msg), "%s,%ld", dir, vol);
            Bridge.notify("direction", msg);

            Monitor.print("dir: ");
            Monitor.println(msg);
        }
    }
}
