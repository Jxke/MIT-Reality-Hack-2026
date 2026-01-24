#include <Arduino_RouterBridge.h>

const int micPins[4] = {A0, A1, A2, A3};

// Tune these for your two-state behavior (~2000 and ~4000)
const int LOW_TH  = 2600;   // below this => inactive
const int HIGH_TH = 3400;   // above this => active

const uint32_t MIN_GAP_MS = 200; // per channel cooldown

bool activeState[4] = {false, false, false, false};
uint32_t lastSendMs[4] = {0, 0, 0, 0};

int readMicFast(int pin)
{
  // Optional tiny averaging to reduce single-sample jitter
  int a = analogRead(pin);
  int b = analogRead(pin);
  int c = analogRead(pin);
  return (a + b + c) / 3;
}

void setup() {
  Bridge.begin();      // keep the proven order
  Monitor.begin();
  delay(200);

  analogReadResolution(12); // 0..4095

  delay(5000); // give Linux/Python time to start + register handlers

  Monitor.println("MCU ready: sending 1..4 via Bridge.notify('mcu_line', msg)");
}

void loop() {
  uint32_t now = millis();

  for (int i = 0; i < 4; i++) {
    int v = readMicFast(micPins[i]);

    // Hysteresis latch (prevents flicker)
    bool wasActive = activeState[i];
    if (v > HIGH_TH) activeState[i] = true;
    else if (v < LOW_TH) activeState[i] = false;

    // Rising edge + cooldown => send event
    if (activeState[i] && !wasActive && (now - lastSendMs[i] > MIN_GAP_MS)) {
      lastSendMs[i] = now;

      int ev = i + 1; // 1..4
      char msg[4];
      snprintf(msg, sizeof(msg), "%d", ev);

      Bridge.notify("mcu_line", msg);

      Monitor.print("sent: ");
      Monitor.print(ev);
      Monitor.print("  v=");
      Monitor.println(v);
    }
  }

  delay(10);
}
