"""
Message bus for coordinating between components
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageBus:
    """Coordinates messages between serial reader, audio processing, and transport server"""
    
    def __init__(self, transport_server, direction_enabled: bool = True):
        self.transport_server = transport_server
        self.direction_enabled = direction_enabled
        
        # Direction tracking for gating
        self.current_direction: Optional[int] = None
        self.current_confidence: float = 0.0
        self.direction_start_time: Optional[float] = None
        self.last_direction_update: float = 0.0
        
        # Audio state
        self.current_audio_energy: float = 0.0
        
    def update_direction(self, direction: int, confidence: float, timestamp: float):
        """
        Update direction data from Arduino
        Returns True if direction is stable and meets gating criteria
        """
        from config import DIRECTION_STABLE_MS, MIN_CONFIDENCE, ENABLE_GATING

        if not self.direction_enabled or not ENABLE_GATING:
            return False
        
        now = timestamp
        
        if self.current_direction != direction:
            # Direction changed
            self.current_direction = direction
            self.current_confidence = confidence
            self.direction_start_time = now
            self.last_direction_update = now
            return False
        
        self.last_direction_update = now
        self.current_confidence = confidence  # Update confidence even if direction unchanged
        
        # Check if direction has been stable long enough
        if self.direction_start_time is None:
            return False
        
        stable_duration = (now - self.direction_start_time) * 1000  # Convert to ms
        
        if stable_duration >= DIRECTION_STABLE_MS and confidence >= MIN_CONFIDENCE:
            return True
        
        return False
    
    def update_audio_energy(self, energy: float):
        """Update current audio energy level"""
        self.current_audio_energy = energy
    
    async def emit_caption(self, 
                          text: str,
                          mode: str,
                          direction: Optional[int] = None,
                          confidence: Optional[float] = None,
                          is_final: bool = True):
        """
        Emit a caption event via TCP
        
        Args:
            text: Caption text
            mode: "speech" or "sound"
            direction: Direction index (0-3) or None
            confidence: Confidence value (0.0-1.0) or None
            is_final: Whether this is a final caption
        """
        from config import MIN_ENERGY, ENABLE_GATING
        
        # Use current direction/confidence if not provided
        if direction is None:
            direction = self.current_direction or 0
        if confidence is None:
            confidence = self.current_confidence
        
        # Check energy threshold
        if self.current_audio_energy < MIN_ENERGY:
            logger.info(f"Skipping caption due to low energy: {self.current_audio_energy:.4f} < {MIN_ENERGY}")
            return
        
        # Check gating criteria
        if not self.is_gating_passed():
            if ENABLE_GATING:
                logger.info("Skipping caption - gating criteria not met")
            return
        
        message = {
            "type": "caption",
            "mode": mode,
            "text": text,
            "isFinal": is_final,
            "direction": direction,
            "confidence": confidence,
            "timestamp": datetime.now().timestamp()
        }
        
        await self.transport_server.broadcast(message)
        logger.info(f"Caption emitted: [{mode}] {text[:50]}... (dir={direction}, conf={confidence:.2f})")
    
    def is_gating_passed(self) -> bool:
        """Check if all gating criteria are met"""
        from config import DIRECTION_STABLE_MS, MIN_CONFIDENCE, MIN_ENERGY, ENABLE_GATING

        if not ENABLE_GATING:
            return True

        if not self.direction_enabled:
            return True
        
        if self.current_direction is None or self.direction_start_time is None:
            return False
        
        import time
        now = time.time()
        stable_duration = (now - self.direction_start_time) * 1000
        
        return (
            stable_duration >= DIRECTION_STABLE_MS and
            self.current_confidence >= MIN_CONFIDENCE and
            self.current_audio_energy >= MIN_ENERGY
        )
