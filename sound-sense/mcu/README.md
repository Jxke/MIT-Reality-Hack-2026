## sketch/sketch.ino — runs on the MCU core (Zephyr RTOS)
Arduino sketch that runs on the hardware MCU. It reads the microphone, does direction sensing, and emits events via Bridge.notify("audio", pkt) and Bridge.notify("direction", ...). You flash this separately — it has nothing to do with arduino-app-cli.

## bridge_shim.py — runs on the Linux MPU as an arduino-app-cli app
The file is deployed to /home/arduino/ArduinoApps/bridge-shim/python/main.py.
rebuild.sh does the sync: `cp "$SCRIPT_DIR/../mcu/bridge_shim.py" /home/arduino/ArduinoApps/bridge-shim/python/main.py`
`arduino-app-cli app restart user:bridge-shim`

arduino-app-cli manages the lifecycle of main.py — starts it, restarts it on crash, runs it inside a container
  with Python + the arduino.app_utils package available.
bridge_shim.py resends the MCU messages to the podman containers.

## Why this indirection exists: 
arduino.app_utils (and thus Bridge) only works from within an arduino-app-cli managed app — it
  talks to arduino-app-cli on 127.0.0.1:8800, which is localhost-only and can't be reached from inside a pipeline container. The
  shim bridges that gap by re-serving the events over plain TCP on port 7000, which the pipeline container can reach because it
  runs with network_mode: host.