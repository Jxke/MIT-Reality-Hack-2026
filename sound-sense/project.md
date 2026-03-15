# Project SoundSense

## Pipeline Server
- Runs on an Arduino Uno Q (debian Linux board)
- Runs processes in podman containers
- Listens to USB microphone audio
- Transcribes speech to text using Whisper.cpp running in the Whisper podman container
- An arduino board connects and sends tcp messages to our server, with number values in the message
- Sends TCP messages to a AR device with the dialog text as a string and the arduino number values

## Arduino Client
- Listens to multiple microphones
- Does some processing (details not important)
- Sends TCP message to Pipeline Server

## AR Device
- Some augmented reality device will receive Pipeline's TCP messages and display text and numbers in a game app