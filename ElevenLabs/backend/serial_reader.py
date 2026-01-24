"""
Serial reader for Arduino direction data
Auto-detects serial port on macOS
"""

import serial
import serial.tools.list_ports
import json
import logging
from typing import Optional, Callable
from config import SERIAL_PORT, SERIAL_BAUD

logger = logging.getLogger(__name__)


def find_arduino_port() -> Optional[str]:
    """
    Auto-detect Arduino serial port on macOS
    Looks for /dev/cu.usbmodem* or /dev/cu.usbserial*
    """
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        port_path = port.device
        if 'usbmodem' in port_path or 'usbserial' in port_path:
            logger.info(f"Found potential Arduino port: {port_path} ({port.description})")
            return port_path
    
    # Fallback: list all available ports
    logger.warning("No USB modem/serial port found. Available ports:")
    for port in ports:
        logger.warning(f"  - {port.device}: {port.description}")
    
    return None


class SerialReader:
    """Reads JSON lines from Arduino serial port"""
    
    def __init__(self, port: Optional[str] = None, baud: int = SERIAL_BAUD):
        self.port = port or SERIAL_PORT or find_arduino_port()
        if not self.port:
            raise ValueError("No serial port specified and auto-detection failed")
        
        self.baud = baud
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        
    def connect(self):
        """Open serial connection"""
        try:
            self.serial_conn = serial.Serial(
                self.port,
                self.baud,
                timeout=1.0,
                write_timeout=1.0
            )
            logger.info(f"Connected to serial port: {self.port} @ {self.baud} baud")
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            raise
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Serial port closed")
    
    def read_line(self) -> Optional[dict]:
        """
        Read a single JSON line from serial
        Returns parsed dict or None if no valid line available
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            line = self.serial_conn.readline().decode('utf-8').strip()
            if not line:
                return None
            
            data = json.loads(line)
            return data
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to parse serial line: {e}")
            return None
        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            return None
    
    def start_reading(self, callback: Callable[[dict], None]):
        """
        Start reading serial data in a loop
        Calls callback with each parsed JSON object
        """
        self.running = True
        
        while self.running:
            data = self.read_line()
            if data:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in serial callback: {e}")
    
    def stop(self):
        """Stop reading loop"""
        self.running = False
