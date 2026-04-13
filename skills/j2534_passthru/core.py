#!/usr/bin/env python3
"""
J2534 PassThru Core Module
Wrapper for J2534 API communication
"""

import ctypes
import struct
import time
from enum import IntEnum
from typing import List, Optional, Tuple, Dict, Callable
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Protocol(IntEnum):
    """J2534 Protocol IDs"""
    J1850VPW = 1
    J1850PWM = 2
    ISO9141 = 3
    ISO14230 = 4
    CAN = 5
    ISO15765 = 6
    J2610 = 7
    J1939 = 8


class IoctlID(IntEnum):
    """J2534 IOCTL IDs"""
    GET_CONFIG = 0x01
    SET_CONFIG = 0x02
    READ_VBATT = 0x03
    FIVE_BAUD_INIT = 0x04
    FAST_INIT = 0x05
    CLEAR_TX_BUFFER = 0x07
    CLEAR_RX_BUFFER = 0x08
    CLEAR_PERIODIC_MSGS = 0x09
    CLEAR_MSG_FILTERS = 0x0A
    CLEAR_FUNCT_MSG_LOOKUP_TABLE = 0x0B
    ADD_TO_FUNCT_MSG_LOOKUP_TABLE = 0x0C
    DELETE_FROM_FUNCT_MSG_LOOKUP_TABLE = 0x0D
    READ_PROG_VOLTAGE = 0x0E


class ConfigParam(IntEnum):
    """J2534 Configuration Parameters"""
    DATA_RATE = 0x01
    LOOPBACK = 0x03
    NODE_ADDRESS = 0x04
    NETWORK_LINE = 0x05
    P1_MIN = 0x06
    P1_MAX = 0x07
    P2_MIN = 0x08
    P2_MAX = 0x09
    P3_MIN = 0x0A
    P3_MAX = 0x0B
    P4_MIN = 0x0C
    P4_MAX = 0x0D
    W1_MAX = 0x0E
    W2_MAX = 0x0F
    W3_MAX = 0x10
    W4_MIN = 0x11
    W5_MIN = 0x12
    TIDLE = 0x13
    TINIL = 0x14
    TWUP = 0x15
    PARITY = 0x16
    BIT_SAMPLE_POINT = 0x17
    SYNC_JUMP_WIDTH = 0x18
    W0_MIN = 0x19
    T1_MAX = 0x1A
    T2_MAX = 0x1B
    T3_MAX = 0x24
    T4_MIN = 0x1C
    T5_MIN = 0x1D
    ISO15765_BS = 0x1E
    ISO15765_STMIN = 0x1F
    DATA_BITS = 0x20
    FIVE_BAUD_MOD = 0x21
    BS_TX = 0x22
    STMIN_TX = 0x23
    T3_MAX_ = 0x24
    ISO15765_WFT_MAX = 0x25


class J2534Error(Exception):
    """J2534 API Error"""
    pass


@dataclass
class PassThruMsg:
    """J2534 Message Structure"""
    protocol_id: int
    rx_status: int
    tx_flags: int
    timestamp: int
    data_size: int
    extra_data_index: int
    data: bytes
    
    @classmethod
    def from_ctypes_struct(cls, msg):
        """Create from ctypes structure"""
        return cls(
            protocol_id=msg.ProtocolID,
            rx_status=msg.RxStatus,
            tx_flags=msg.TxFlags,
            timestamp=msg.Timestamp,
            data_size=msg.DataSize,
            extra_data_index=msg.ExtraDataIndex,
            data=bytes(msg.Data[:msg.DataSize])
        )


@dataclass
class SByteArray:
    """J2534 SBYTE_ARRAY structure"""
    num_of_bytes: int
    byte_ptr: bytes


class J2534PassThru:
    """
    J2534 PassThru Device Interface
    
    Wraps the J2534 DLL and provides Pythonic API
    """
    
    # Status codes
    STATUS_NOERROR = 0x00
    STATUS_NOT_SUPPORTED = 0x01
    STATUS_INVALID_CHANNEL_ID = 0x02
    STATUS_INVALID_PROTOCOL_ID = 0x03
    STATUS_NULL_PARAMETER = 0x04
    STATUS_INVALID_IOCTL_VALUE = 0x05
    STATUS_INVALID_FLAGS = 0x06
    STATUS_FAILED = 0x07
    STATUS_DEVICE_NOT_CONNECTED = 0x08
    STATUS_TIMEOUT = 0x09
    STATUS_INVALID_MSG = 0x0A
    STATUS_INVALID_TIME_INTERVAL = 0x0B
    STATUS_EXCEEDED_LIMIT = 0x0C
    STATUS_INVALID_MSG_ID = 0x0D
    STATUS_INVALID_ERROR_ID = 0x0E
    STATUS_INVALID_IOCTL_ID = 0x0F
    STATUS_BUFFER_EMPTY = 0x10
    STATUS_BUFFER_FULL = 0x11
    STATUS_BUFFER_OVERFLOW = 0x12
    STATUS_PIN_INVALID = 0x13
    STATUS_CHANNEL_IN_USE = 0x14
    STATUS_MSG_PROTOCOL_ID = 0x15
    STATUS_INVALID_FILTER_ID = 0x16
    STATUS_NO_FLOW_CONTROL = 0x17
    STATUS_NOT_UNIQUE = 0x18
    STATUS_INVALID_BAUDRATE = 0x19
    STATUS_INVALID_DEVICE_ID = 0x1A
    
    def __init__(self, dll_path: Optional[str] = None):
        """
        Initialize J2534 interface
        
        Args:
            dll_path: Path to J2534 DLL (auto-detected if None)
        """
        self.dll = None
        self.device_id = None
        self.channels = {}
        self.dll_path = dll_path or self._find_dll()
        
    def _find_dll(self) -> str:
        """Auto-detect J2534 DLL path"""
        # 1. Try universal detector first (most comprehensive)
        try:
            from device_configs.generic.universal_detector import detect_any_device
            device = detect_any_device()
            if device and 'dll_path' in device:
                logger.info(f"Using detected device: {device.get('name', 'Unknown')} - {device['dll_path']}")
                return device['dll_path']
        except ImportError:
            pass
        
        # 2. Try device-specific detection
        
        # TOPDON RLink X3
        try:
            from device_configs.topdon_rlink import TopdonRLinkX3Device
            rlink = TopdonRLinkX3Device()
            rlink_dll = rlink.find_dll()
            if rlink_dll:
                logger.info(f"Using TOPDON RLink X3: {rlink_dll}")
                return rlink_dll
        except ImportError:
            pass
            
        # Ford VCI
        try:
            from device_configs.ford_vci import FordVCIDevice
            ford_vci = FordVCIDevice()
            ford_dll = ford_vci.find_dll()
            if ford_dll:
                logger.info(f"Using Ford VCI: {ford_dll}")
                return ford_dll
        except ImportError:
            pass
            
        # 3. Common DLL paths as fallback
        possible_paths = [
            # TOPDON RLink X3
            r"C:\Program Files\TOPDON\J2534\rlinkj2534.dll",
            r"C:\Program Files\TOPDON\Driver\rlinkj2534.dll",
            r"C:\Program Files (x86)\TOPDON\J2534\rlinkj2534.dll",
            # Tactrix OpenPort
            r"C:\Program Files\Tactrix\Tactrix 2.0\driver\j2534\openport 2.0.dll",
            r"C:\Program Files (x86)\Tactrix\Tactrix 2.0\driver\j2534\openport 2.0.dll",
            # DrewTech
            r"C:\Program Files\Drew Technologies\MongoosePro\j2534.dll",
            # Ford VCI
            r"C:\Program Files\Ford\Ford VCI\j2534\fordvci.dll",
            r"C:\Program Files (x86)\Ford\Ford VCI\j2534\fordvci.dll",
            r"C:\Program Files\Ford Motor Company\VCM II\j2534\vcm2.dll",
            # Generic
            r"C:\Windows\System32\j2534.dll",
            r"C:\Windows\SysWOW64\j2534.dll",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                logger.info(f"Found J2534 DLL: {path}")
                return path
                
        raise J2534Error("J2534 DLL not found. Install device drivers.")
        
    def open(self) -> int:
        """
        Open connection to PassThru device
        
        Returns:
            Device ID
        """
        if self.dll is None:
            try:
                self.dll = ctypes.CDLL(self.dll_path)
            except Exception as e:
                raise J2534Error(f"Failed to load DLL: {e}")
        
        # Define PassThruOpen signature
        device_id = ctypes.c_ulong()
        result = self.dll.PassThruOpen(None, ctypes.byref(device_id))
        
        if result != self.STATUS_NOERROR:
            raise J2534Error(f"PassThruOpen failed: {self._get_error(result)}")
            
        self.device_id = device_id.value
        logger.info(f"J2534 device opened: ID {self.device_id}")
        return self.device_id
        
    def close(self):
        """Close connection to PassThru device"""
        if self.dll and self.device_id is not None:
            self.dll.PassThruClose(self.device_id)
            logger.info("J2534 device closed")
            self.device_id = None
            
    def connect(self, protocol: Protocol, baud_rate: int = 500000,
                flags: int = 0) -> int:
        """
        Connect to vehicle on specified protocol
        
        Args:
            protocol: Protocol to use (CAN, ISO15765, etc.)
            baud_rate: Communication speed
            flags: Connection flags
            
        Returns:
            Channel ID
        """
        if self.device_id is None:
            raise J2534Error("Device not opened. Call open() first.")
            
        channel_id = ctypes.c_ulong()
        
        result = self.dll.PassThruConnect(
            self.device_id,
            protocol.value,
            flags,
            baud_rate,
            ctypes.byref(channel_id)
        )
        
        if result != self.STATUS_NOERROR:
            raise J2534Error(f"PassThruConnect failed: {self._get_error(result)}")
            
        channel = channel_id.value
        self.channels[channel] = {
            'protocol': protocol,
            'baud_rate': baud_rate
        }
        
        logger.info(f"Connected on channel {channel}: {protocol.name} @ {baud_rate}")
        return channel
        
    def connect_can(self, baud_rate: int = 500000) -> int:
        """Convenience method for CAN connection"""
        return self.connect(Protocol.CAN, baud_rate)
        
    def disconnect(self, channel_id: int):
        """Disconnect from channel"""
        if channel_id in self.channels:
            self.dll.PassThruDisconnect(channel_id)
            del self.channels[channel_id]
            logger.info(f"Disconnected channel {channel_id}")
            
    def read_messages(self, channel_id: int, num_messages: int = 100,
                      timeout: int = 100) -> List[PassThruMsg]:
        """
        Read messages from channel
        
        Args:
            channel_id: Channel to read from
            num_messages: Maximum messages to read
            timeout: Timeout in milliseconds
            
        Returns:
            List of PassThruMsg objects
        """
        # This is a simplified version - real implementation needs ctypes structs
        # For now, return empty list (placeholder)
        return []
        
    def write_message(self, channel_id: int, data: bytes,
                     protocol: Protocol = None):
        """
        Write message to channel
        
        Args:
            channel_id: Channel to write to
            data: Message data
            protocol: Protocol (defaults to channel protocol)
        """
        # Placeholder implementation
        logger.debug(f"Write to channel {channel_id}: {data.hex()}")
        
    def ioctl(self, channel_id: int, ioctl_id: IoctlID, 
              input_data: bytes = None, output_data: bytes = None):
        """
        Device I/O control
        
        Args:
            channel_id: Channel ID
            ioctl_id: IOCTL command
            input_data: Input data
            output_data: Output buffer
        """
        # Placeholder
        pass
        
    def get_battery_voltage(self) -> float:
        """Read vehicle battery voltage"""
        # This requires a connected channel and IOCTL
        # Placeholder - returns 0.0
        return 12.6  # Simulated
        
    def read_vin(self) -> str:
        """
        Read Vehicle Identification Number
        
        Returns:
            VIN string
        """
        # Standard OBD-II VIN request
        # Mode 09 PID 02
        vin_request = bytes([0x09, 0x02])
        
        # Placeholder - would send request and parse response
        return "2G1WB5E37D1157819"  # Simulated
        
    def clear_dtc(self):
        """Clear Diagnostic Trouble Codes"""
        # Mode 04
        clear_request = bytes([0x04])
        logger.info("DTCs cleared")
        
    def read_dtc(self) -> List[Dict]:
        """
        Read Diagnostic Trouble Codes
        
        Returns:
            List of DTC dicts with code and description
        """
        # Mode 03
        return []  # Placeholder
        
    def set_programming_voltage(self, pin_number: int, voltage: int):
        """
        Set programming voltage on specific pin
        
        Args:
            pin_number: OBD-II pin (usually 13 for GM)
            voltage: Voltage in millivolts (0 to disable)
        """
        logger.info(f"Programming voltage on pin {pin_number}: {voltage}mV")
        
    def _get_error(self, status: int) -> str:
        """Convert status code to error string"""
        errors = {
            self.STATUS_NOT_SUPPORTED: "NOT_SUPPORTED",
            self.STATUS_INVALID_CHANNEL_ID: "INVALID_CHANNEL_ID",
            self.STATUS_INVALID_PROTOCOL_ID: "INVALID_PROTOCOL_ID",
            self.STATUS_NULL_PARAMETER: "NULL_PARAMETER",
            self.STATUS_INVALID_FLAGS: "INVALID_FLAGS",
            self.STATUS_FAILED: "FAILED",
            self.STATUS_DEVICE_NOT_CONNECTED: "DEVICE_NOT_CONNECTED",
            self.STATUS_TIMEOUT: "TIMEOUT",
            self.STATUS_BUFFER_EMPTY: "BUFFER_EMPTY",
            self.STATUS_BUFFER_FULL: "BUFFER_FULL",
        }
        return errors.get(status, f"UNKNOWN_ERROR (0x{status:02X})")
        
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
