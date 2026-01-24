"""
SoundSight Backend - Main orchestrator
Connects Arduino serial, audio capture, VAD, STT, classifier, and TCP client
"""

import asyncio
import logging
import threading
import time
from typing import Optional
import numpy as np
from config import LOG_LEVEL, ENABLE_SERIAL
from serial_reader import SerialReader
from audio_stream import AudioStream
from vad import VAD
from stt_elevenlabs import ElevenLabsSTT
from classifier_mediapipe import MediaPipeClassifier
from tcp_client import TCPClient
from message_bus import MessageBus

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SoundSightBackend:
    """Main backend orchestrator"""
    
    def __init__(self):
        self.serial_reader: Optional[SerialReader] = None
        self.audio_stream = AudioStream()
        self.vad = VAD()
        self.stt = ElevenLabsSTT()
        self.classifier = MediaPipeClassifier()
        self.tcp_client = TCPClient()
        self.message_bus = MessageBus(self.tcp_client, direction_enabled=ENABLE_SERIAL)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.last_energy_log = 0.0

        if ENABLE_SERIAL:
            try:
                self.serial_reader = SerialReader()
            except Exception as e:
                logger.warning(f"Serial disabled: {e}")
                self.message_bus.direction_enabled = False
        
        self.running = False
        self.serial_thread: Optional[threading.Thread] = None
        self.audio_thread: Optional[threading.Thread] = None
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing SoundSight backend...")
        
        # Initialize TCP client
        await self.tcp_client.start()
        
        # STT is initialized in __init__ (will raise error if API key missing)
        logger.info("ElevenLabs STT initialized")
        
        # Initialize classifier
        self.classifier.initialize()
        
        logger.info("Initialization complete")
    
    def handle_serial_data(self, data: dict):
        """Handle incoming serial data from Arduino"""
        try:
            direction = data.get('direction', 0)
            confidence = data.get('confidence', 0.0)
            timestamp = time.time()
            
            # Update message bus with direction data
            self.message_bus.update_direction(direction, confidence, timestamp)
            
            logger.debug(f"Direction: {direction}, Confidence: {confidence:.3f}")
        except Exception as e:
            logger.error(f"Error handling serial data: {e}")
    
    def handle_audio_chunk(self, audio_chunk: np.ndarray):
        """Handle incoming audio chunk"""
        try:
            # Update energy level
            energy = AudioStream.get_rms_energy(audio_chunk)
            self.message_bus.update_audio_energy(energy)
            now = time.time()
            if now - self.last_energy_log >= 2.0:
                logger.info(
                    f"Audio energy: {energy:.4f} (vad_start={self.vad.start_threshold:.3f}, "
                    f"vad_stop={self.vad.stop_threshold:.3f})"
                )
                self.last_energy_log = now
            
            # Process with VAD
            is_speech, complete_audio = self.vad.process(audio_chunk)
            
            if complete_audio is not None:
                # Speech segment complete, process it
                if self.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.process_speech_segment(complete_audio), self.loop
                    )
            elif not is_speech:
                # Not speech, classify as sound event
                if self.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.process_sound_event(audio_chunk), self.loop
                    )
                
        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")
    
    async def process_speech_segment(self, audio: np.ndarray):
        """Process complete speech segment with STT"""
        try:
            # Transcribe (blocking I/O offloaded to thread)
            sample_rate = self.audio_stream.sample_rate
            text = await asyncio.to_thread(self.stt.transcribe, audio, sample_rate)
            logger.info(f"Caption: {text}")
            
            if text and text != "[NO_SPEECH]" and text != "[TRANSCRIPTION_ERROR]":
                # Get current direction and confidence from message bus
                direction = self.message_bus.current_direction or 0
                confidence = self.message_bus.current_confidence
                
                # Emit caption
                await self.message_bus.emit_caption(
                    text=text,
                    mode="speech",
                    direction=direction,
                    confidence=confidence,
                    is_final=True
                )
        except Exception as e:
            logger.error(f"Error processing speech segment: {e}")
    
    async def process_sound_event(self, audio_chunk: np.ndarray):
        """Process non-speech audio with classifier"""
        try:
            # Only classify if energy is significant
            energy = AudioStream.get_rms_energy(audio_chunk)
            if energy < 0.01:  # Skip very quiet sounds
                return
            
            # Classify (potentially heavy; offload to thread)
            label = await asyncio.to_thread(self.classifier.classify, audio_chunk)
            
            if label and label != "[SILENCE]":
                direction = self.message_bus.current_direction or 0
                confidence = self.message_bus.current_confidence
                
                # Emit caption
                await self.message_bus.emit_caption(
                    text=label,
                    mode="sound",
                    direction=direction,
                    confidence=confidence,
                    is_final=True
                )
        except Exception as e:
            logger.error(f"Error processing sound event: {e}")
    
    def start_serial_reader(self):
        """Start serial reader in background thread"""
        if not self.serial_reader:
            logger.info("Serial reader disabled")
            return

        def serial_loop():
            try:
                self.serial_reader.connect()
                self.serial_reader.start_reading(self.handle_serial_data)
            except Exception as e:
                logger.error(f"Serial reader error: {e}")
                self.message_bus.direction_enabled = False
        
        self.serial_thread = threading.Thread(target=serial_loop, daemon=True)
        self.serial_thread.start()
    
    def start_audio_stream(self):
        """Start audio stream in background thread"""
        def audio_loop():
            try:
                self.audio_stream.start(self.handle_audio_chunk)
            except Exception as e:
                logger.error(f"Audio stream error: {e}")
                self.running = False
        
        self.audio_thread = threading.Thread(target=audio_loop, daemon=True)
        self.audio_thread.start()
    
    async def run(self):
        """Main run loop"""
        self.running = True
        self.loop = asyncio.get_running_loop()
        
        # Start serial reader
        logger.info("Starting serial reader...")
        self.start_serial_reader()
        
        # Start audio stream
        logger.info("Starting audio stream...")
        self.start_audio_stream()
        
        logger.info("SoundSight backend running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown"""
        self.running = False
        
        # Stop serial reader
        if self.serial_reader:
            self.serial_reader.stop()
            self.serial_reader.disconnect()
        
        # Stop audio stream
        if self.audio_stream:
            self.audio_stream.stop()
        
        # Stop TCP client
        if self.tcp_client:
            await self.tcp_client.stop()
        
        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    backend = SoundSightBackend()
    await backend.initialize()
    await backend.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
