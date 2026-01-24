"""
Audio stream capture from USB microphone
"""

import sounddevice as sd
import numpy as np
import logging
from typing import Callable, Optional
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE

logger = logging.getLogger(__name__)


class AudioStream:
    """Captures audio from default microphone in chunks"""
    
    def __init__(self, 
                 sample_rate: int = AUDIO_SAMPLE_RATE,
                 channels: int = AUDIO_CHANNELS,
                 chunk_size: int = AUDIO_CHUNK_SIZE):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.stream: Optional[sd.InputStream] = None
        self.running = False
        
    def start(self, callback: Callable[[np.ndarray], None]):
        """
        Start audio stream
        Calls callback with each audio chunk (numpy array)
        """
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            if self.running:
                # Convert to mono if needed
                audio_chunk = indata[:, 0] if self.channels == 1 else np.mean(indata, axis=1)
                callback(audio_chunk)
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype=np.float32
            )
            self.running = True
            self.stream.start()
            logger.info(f"Audio stream started: {self.sample_rate}Hz, {self.channels} channel(s), chunk size {self.chunk_size}")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            logger.error("Make sure microphone permissions are granted in System Settings")
            raise
    
    def stop(self):
        """Stop audio stream"""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Audio stream stopped")
    
    @staticmethod
    def list_devices():
        """List available audio input devices"""
        devices = sd.query_devices()
        logger.info("Available audio input devices:")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                logger.info(f"  [{i}] {device['name']} - {device['max_input_channels']} channel(s) @ {device['default_samplerate']}Hz")
    
    @staticmethod
    def get_rms_energy(audio: np.ndarray) -> float:
        """Calculate RMS energy of audio chunk"""
        return float(np.sqrt(np.mean(audio ** 2)))
