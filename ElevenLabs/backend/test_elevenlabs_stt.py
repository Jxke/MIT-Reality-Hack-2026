#!/usr/bin/env python3
"""
Test script for ElevenLabs Speech-to-Text
Records 3 seconds from default microphone and transcribes
"""

import os
import sys
import time
import numpy as np
import sounddevice as sd
from stt_elevenlabs import ElevenLabsSTT

# Check for API key
if not os.getenv("ELEVENLABS_API_KEY"):
    print("Error: ELEVENLABS_API_KEY environment variable not set")
    print("Set it with: export ELEVENLABS_API_KEY='your_key_here'")
    sys.exit(1)

def record_audio(duration: float = 3.0, sample_rate: int = 16000) -> np.ndarray:
    """
    Record audio from default microphone
    
    Args:
        duration: Recording duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Audio samples as numpy array (float32, mono)
    """
    print(f"Recording {duration} seconds... Speak now!")
    
    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()  # Wait until recording is finished
        print("Recording complete!")
        return audio.flatten()
    except Exception as e:
        print(f"Error recording audio: {e}")
        print("Make sure microphone permissions are granted in System Settings")
        sys.exit(1)

def main():
    """Main test function"""
    print("ElevenLabs STT Test")
    print("=" * 50)
    
    # Initialize STT
    try:
        stt = ElevenLabsSTT()
        print("ElevenLabs STT initialized successfully")
    except Exception as e:
        print(f"Failed to initialize STT: {e}")
        sys.exit(1)
    
    # Record audio
    audio = record_audio(duration=3.0)
    
    # Transcribe
    print("\nTranscribing...")
    try:
        text = stt.transcribe(audio, sample_rate=16000)
        print(f"\nTranscription: {text}")
    except Exception as e:
        print(f"Transcription failed: {e}")
        sys.exit(1)
    
    print("\nTest complete!")

if __name__ == "__main__":
    main()
