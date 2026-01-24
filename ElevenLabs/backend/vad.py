"""
Voice Activity Detection (VAD) using energy-based approach
"""

import numpy as np
import logging
from typing import Optional
from config import VAD_START_THRESHOLD, VAD_STOP_THRESHOLD, VAD_HANGOVER_BLOCKS
from audio_stream import AudioStream

logger = logging.getLogger(__name__)


class VAD:
    """
    Simple energy-based VAD
    Detects speech when energy exceeds start threshold
    Stops detecting after energy drops below stop threshold for hangover duration
    """
    
    def __init__(self,
                 start_threshold: float = VAD_START_THRESHOLD,
                 stop_threshold: float = VAD_STOP_THRESHOLD,
                 hangover_blocks: int = VAD_HANGOVER_BLOCKS):
        self.start_threshold = start_threshold
        self.stop_threshold = stop_threshold
        self.hangover_blocks = hangover_blocks
        
        self.is_speech = False
        self.hangover_counter = 0
        self.speech_buffer: list = []
        
    def process(self, audio_chunk: np.ndarray) -> tuple[bool, Optional[np.ndarray]]:
        """
        Process audio chunk and determine if speech is detected
        
        Returns:
            (is_speech, complete_audio_or_none)
            - is_speech: True if currently detecting speech
            - complete_audio_or_none: Full audio buffer when speech ends, None otherwise
        """
        energy = AudioStream.get_rms_energy(audio_chunk)
        
        if not self.is_speech:
            # Not currently detecting speech
            if energy >= self.start_threshold:
                # Start detecting speech
                self.is_speech = True
                self.hangover_counter = 0
                self.speech_buffer = [audio_chunk]
                logger.info(f"Speech started (energy: {energy:.4f})")
                return (True, None)
            else:
                return (False, None)
        else:
            # Currently detecting speech
            self.speech_buffer.append(audio_chunk)
            
            if energy < self.stop_threshold:
                self.hangover_counter += 1
                if self.hangover_counter >= self.hangover_blocks:
                    # Speech ended
                    self.is_speech = False
                    complete_audio = np.concatenate(self.speech_buffer)
                    self.speech_buffer = []
                    logger.info(
                        f"Speech ended (energy: {energy:.4f}, duration: {len(complete_audio)/16000:.2f}s)"
                    )
                    return (False, complete_audio)
            else:
                # Reset hangover counter if energy goes back up
                self.hangover_counter = 0
            
            return (True, None)
    
    def reset(self):
        """Reset VAD state"""
        self.is_speech = False
        self.hangover_counter = 0
        self.speech_buffer = []
