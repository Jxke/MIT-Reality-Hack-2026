"""
Speech-to-Text using ElevenLabs API
"""

import io
import wave
import logging
import os
import numpy as np
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class ElevenLabsSTT:
    """Speech-to-text using ElevenLabs batch API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.elevenlabs.io"):
        """
        Initialize ElevenLabs STT client
        
        Args:
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            base_url: API base URL (default: https://api.elevenlabs.io)
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key not provided. Set ELEVENLABS_API_KEY environment variable.")
        
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/v1/speech-to-text"
        
        logger.info("ElevenLabs STT initialized")
    
    def _audio_to_wav_bytes(self, audio: np.ndarray, sample_rate: int = 16000) -> bytes:
        """
        Convert numpy float32 audio array to WAV file bytes (16-bit PCM)
        
        Args:
            audio: Audio samples as numpy array (float32, mono, range [-1, 1])
            sample_rate: Sample rate in Hz
        
        Returns:
            WAV file bytes
        """
        # Ensure audio is float32 and in valid range
        audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
        
        # Convert to int16 PCM
        audio_int16 = (audio * 32767.0).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        wav_bytes = wav_buffer.getvalue()
        wav_buffer.close()
        
        return wav_bytes
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, language: Optional[str] = None) -> str:
        """
        Transcribe audio to text using ElevenLabs API
        
        Args:
            audio: Audio samples as numpy array (float32, mono, range [-1, 1])
            sample_rate: Sample rate in Hz (default 16000)
            language: Optional language code (e.g., "en"). If None, API auto-detects.
        
        Returns:
            Transcribed text string, or "[TRANSCRIPTION_ERROR]" on failure
        """
        try:
            # Convert audio to WAV bytes
            wav_bytes = self._audio_to_wav_bytes(audio, sample_rate)
            
            # Prepare multipart form data
            files = {
                'file': ('audio.wav', wav_bytes, 'audio/wav')
            }
            
            # Prepare headers
            headers = {
                'xi-api-key': self.api_key,
                'Accept': 'application/json'
            }
            
            # Optional: add language parameter if provided
            data = {
                "model_id": "scribe_v1"
            }
            if language:
                data['language'] = language
            
            # Make API request
            logger.info(f"Sending audio to ElevenLabs ({len(wav_bytes)} bytes)")
            response = requests.post(
                self.endpoint,
                headers=headers,
                files=files,
                data=data,
                timeout=30.0  # 30 second timeout
            )
            
            # Check response status
            response.raise_for_status()
            logger.info(f"ElevenLabs response: {response.status_code}")
            
            # Parse JSON response
            result = response.json()
            logger.info(f"ElevenLabs response payload: {result}")
            
            # Extract transcription text (try common response keys)
            text = None
            if isinstance(result, dict):
                text = result.get('text') or result.get('transcript') or result.get('transcription')
            elif isinstance(result, str):
                text = result
            
            if text:
                text = str(text).strip()
                logger.debug(f"Transcribed: {text}")
                return text if text else "[NO_SPEECH]"
            else:
                logger.warning(f"Unexpected API response format: {result}")
                return "[TRANSCRIPTION_ERROR]"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ElevenLabs API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"API error details: {error_detail}")
                except:
                    logger.error(f"API error response: {e.response.text}")
            return "[TRANSCRIPTION_ERROR]"
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return "[TRANSCRIPTION_ERROR]"
