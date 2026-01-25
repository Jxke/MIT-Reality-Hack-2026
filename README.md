# SoundSense - Live Captions and Directional Audio display for AR viewing
Built for MIT Reality Hack 2026, to help people with audio impairments.

[Devpost Page](https://devpost.com/software/soundsense-tfqiv9)

## Steps to Replicate
Note: Some of the code was left on our board and aren't in this repo... but here are the steps to replicate what we built.
- Build an acoustic array of sound sensors, preferably microphones. We used the KY-037 Sound Sensor.
- Connect sensors to Arduino Uno Q.
- Arduino Uno Q publishes sound sensor data over serial to the Arduino Uno Q's Debian Linux MPU, using Rami's [DirectBridge](https://github.com/ramalamadingdong/bridge_direct) to open a socket instead of using Arduino App Lab.
- Build the [Whisper.cpp](https://github.com/ggml-org/whisper.cpp) model on the Debian machine. We used one of the tiny models. As a backup we had an API to ElevenLabs to provide higher quality speech to text.
- If you chose to build the acoustic array out of microphones, pass the microphone data over serial to the Debian side. We had an external microphone connected to the Debian machine to pick up vocals since the sound sensors are cheap and output only binary (noise or no noise).
- Build .wav files out of microphone data, periodically sending them to the Whisper Model.
- Take the output captions from Whisper and build tcp messages to send to the AR Unity Project.
- Build an AR Unity project that shows users the direction of the highest sound amplitude (using smooth gradient indicators on the edges of user's vision).
- Build caption display boxes that appear in the AR view.
- (optional) Connect [Google's Mediapipe Image Classifier](https://ai.google.dev/edge/mediapipe/solutions/vision/image_classifier) to move the caption boxes to be in front of the speaker.
