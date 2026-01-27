"""
Local Whisper transcription using whisper.cpp
Runs whisper-cli on audio files or streams
"""

import subprocess
import logging
import numpy as np
import soundfile as sf
import tempfile
import os
from typing import Optional
from config import WHISPER_MODEL_PATH, WHISPER_CLI_PATH, AUDIO_SAMPLE_RATE

logger = logging.getLogger(__name__)


class WhisperLocal:
    """Transcribe audio using local whisper.cpp CLI"""
    
    def __init__(self, 
                 model_path: str = WHISPER_MODEL_PATH,
                 cli_path: str = WHISPER_CLI_PATH,
                 language: str = "en"):
        self.model_path = model_path
        self.cli_path = cli_path
        self.language = language
        self.sample_rate = AUDIO_SAMPLE_RATE
        
        # Validate paths
        if not os.path.exists(self.cli_path):
            raise FileNotFoundError(f"whisper-cli not found at {self.cli_path}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Whisper model not found at {self.model_path}")
        
        logger.info(f"WhisperLocal initialized with model: {self.model_path}")
        logger.info(f"Using CLI: {self.cli_path}")
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = None) -> str:
        """
        Transcribe audio chunk using whisper.cpp CLI
        
        Args:
            audio: Audio samples as numpy array (mono, float32)
            sample_rate: Sample rate (defaults to AUDIO_SAMPLE_RATE)
        
        Returns:
            Transcribed text or empty string if no speech detected
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            
            # Write audio to temporary WAV file
            sf.write(tmp_path, audio, sample_rate)
            
            # Run whisper-cli
            cmd = [
                self.cli_path,
                "-m", self.model_path,
                "-f", tmp_path,
                "-l", self.language,
                "--no-timestamps",
            ]
            
            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            if result.returncode != 0:
                logger.error(f"Whisper transcription failed: {result.stderr}")
                return ""
            
            # Parse output - whisper-cli outputs text with timing info, extract just the text
            text = result.stdout.strip()
            
            # Remove timing brackets if present (e.g., "[00:00:00.000 --> 00:00:01.000]")
            import re
            text = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\]', '', text)
            text = text.strip()
            
            if not text:
                logger.info("No speech detected in audio")
                return ""
            
            logger.info(f"Transcription: {text}")
            return text
            
        except subprocess.TimeoutExpired:
            logger.error("Whisper transcription timed out")
            return ""
        except Exception as e:
            logger.error(f"Error during whisper transcription: {e}")
            return ""
