"""
Speech-to-Text using faster-whisper
"""

import logging
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel
from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logger = logging.getLogger(__name__)


class WhisperSTT:
    """Speech-to-text using faster-whisper"""
    
    def __init__(self,
                 model_size: str = WHISPER_MODEL,
                 device: str = WHISPER_DEVICE,
                 compute_type: str = WHISPER_COMPUTE_TYPE):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        
    def initialize(self):
        """Load Whisper model (lazy initialization)"""
        if self.model is None:
            try:
                logger.info(f"Loading Whisper model: {self.model_size} ({self.device}, {self.compute_type})")
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio to text
        
        Args:
            audio: Audio samples as numpy array (float32, mono)
            sample_rate: Sample rate in Hz (default 16000)
        
        Returns:
            Transcribed text string
        """
        if self.model is None:
            self.initialize()
        
        try:
            # faster-whisper expects int16 audio
            audio_int16 = (audio * 32767.0).astype(np.int16)
            
            segments, info = self.model.transcribe(
                audio_int16,
                beam_size=5,
                language="en",  # Can be made configurable
                vad_filter=True,  # Use built-in VAD (we also have our own)
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            result = " ".join(text_parts).strip()
            logger.debug(f"Transcribed: {result}")
            return result if result else "[NO_SPEECH]"
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return "[TRANSCRIPTION_ERROR]"
