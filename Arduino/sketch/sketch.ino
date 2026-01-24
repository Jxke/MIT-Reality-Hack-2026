#include <Arduino_RouterBridge.h>

const int micPin0 = A0;
const int micPin1 = A1;
const int micPin2 = A2;
const int micPin3 = A3;

void setup() {
  Monitor.begin();
  delay(200);
  analogReadResolution(12); // 0..4095 :contentReference[oaicite:4]{index=4}
  Monitor.println("Mic p2p test");
}

void loop() {
  // int minV = 4095, maxV = 0;
  // const uint32_t windowMs = 30;
  // uint32_t t0 = micros();

  // while (micros() - t0 < windowMs * 1000) {
  //   int v = analogRead(micPin);
  //   if (v < minV) minV = v;
  //   if (v > maxV) maxV = v;
  // }

  // int mid = (minV + maxV) / 2;
  // int p2p = (maxV - minV);

  int mic0out = getMicAmp(micPin0);
  int mic1out = getMicAmp(micPin1);
  int mic2out = getMicAmp(micPin2);
  int mic3out = getMicAmp(micPin3);
  if (mic0out < 4000)
  {
      Monitor.print("\nmic0: ");
      Monitor.println(mic0out);
  }
  if (mic1out < 4000)
  {
      Monitor.print("\nmic1: ");
      Monitor.println(mic1out);
  }
  if (mic2out < 4000)
  {
      Monitor.print("\nmic2: ");
      Monitor.println(mic2out);
  }
  if (mic3out < 4000)
  {
      Monitor.print("\nmic3: ");
      Monitor.println(mic3out);
  }
  // Monitor.print("\nmic0: ");
  // Monitor.println(mic0out);
  // Monitor.print("\nmic1: ");
  // Monitor.println(mic1out);
  // Monitor.print("\nmic2: ");
  // Monitor.println(mic2out);
  // Monitor.print("\nmic3: ");
  // Monitor.println(mic3out);
  
  
  // Monitor.print("mid=");
  // Monitor.print(mid);
  // Monitor.print(" p2p=");
  // Monitor.println(p2p);

  delay(50);
}

int getMicAmp(int inputPin)
{
   int minV = 4095, maxV = 0;
  const uint32_t windowMs = 30;
  uint32_t t0 = micros();

  while (micros() - t0 < windowMs * 1000) {
    int v = analogRead(inputPin);
    if (v < minV) minV = v;
    if (v > maxV) maxV = v;
  }
  
  int mid = (minV + maxV) / 2;
  return mid;
}
