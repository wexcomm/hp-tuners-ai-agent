#!/usr/bin/env python3
"""
Constants for HPT Converter and J2534 Passthru

This module contains all magic numbers and platform-specific constants
to improve code maintainability and readability.
"""

from enum import IntEnum

# =============================================================================
# Platform Flash Sizes
# =============================================================================

class FlashSize:
    """Flash memory sizes in bytes for different ECU platforms"""
    GM_E37 = 1048576  # 1MB - Chevrolet Impala LFX 3.6L V6
    GM_E38 = 2097152  # 2MB
    GM_E39 = 2097152  # 2MB
    FORD_PCM = 1572864  # 1.5MB
    FORD_TCM = 786432  # 768KB
    CHRYSLER_PCM = 1048576  # 1MB
    CHRYSLER_TCM = 524288  # 512KB


# =============================================================================
# Battery / Voltage Constants
# =============================================================================

class Voltage:
    """Voltage thresholds and constants"""
    MIN_BATTERY_FLASH = 12.0  # Minimum battery voltage for safe flashing
    MIN_BATTERY_DIAG = 11.5  # Minimum for diagnostics
    NOMINAL_BATTERY = 13.5  # Nominal voltage
    MAX_BATTERY = 15.0  # Maximum expected voltage
    PROGRAMMING_VOLTAGE = 18.0  # Voltage applied during programming


# =============================================================================
# J2534 Protocol IDs
# =============================================================================

class Protocol(IntEnum):
    """J2534 protocol identifiers"""
    CAN = 5
    ISO15765 = 6
    J1850VPW = 1
    J1850PWM = 2
    ISO9141 = 3
    ISO14230 = 4
    SCI_A = 7
    SCI_B = 8


# =============================================================================
# J2534 Error Codes
# =============================================================================

class ErrorCode(IntEnum):
    """J2534 error/status codes"""
    STATUS_NOERROR = 0x00
    ERR_NOT_SUPPORTED = 0x01
    ERR_INVALID_CHANNEL_ID = 0x02
    ERR_INVALID_PROTOCOL_ID = 0x03
    ERR_NULL_PARAMETER = 0x04
    ERR_INVALID_IOCTL_VALUE = 0x05
    ERR_INVALID_FLAGS = 0x06
    ERR_FAILED = 0x07
    ERR_DEVICE_NOT_CONNECTED = 0x08
    ERR_TIMEOUT = 0x09
    ERR_INVALID_MESSAGE = 0x0A
    ERR_INVALID_TIME_INTERVAL = 0x0B
    ERR_EXCEEDED_LIMIT = 0x0C
    ERR_INVALID_MSG_DATA_LENGTH = 0x0D
    ERR_INVALID_J2534_HANDLE = 0x0E
    ERR_BUFFER_EMPTY = 0x0F
    ERR_BUFFER_FULL = 0x10
    ERR_INCORRECT_MODE = 0x11
    ERR_INVALID_BAUDRATE = 0x12
    ERR_INVALID_DEVICE_ID = 0x13


# =============================================================================
# HPT File Format Constants
# =============================================================================

class HPTFormat:
    """HPT file format constants"""
    HEADER_SIZE = 512
    MAGIC_HEADER = b"HPT\x00"
    CURRENT_VERSION = 2
    MAX_METADATA_SIZE = 65536  # 64KB
    MAX_BINARY_SIZE = 16777216  # 16MB


# =============================================================================
# Compression Constants
# =============================================================================

class Compression:
    """Compression settings"""
    DEFAULT_LEVEL = 6
    MIN_LEVEL = 0
    MAX_LEVEL = 9
    BEST_SPEED = 1
    BEST_COMPRESSION = 9


# =============================================================================
# CAN Bus Constants
# =============================================================================

class CAN:
    """CAN bus constants"""
    STANDARD_ID_MASK = 0x7FF
    EXTENDED_ID_MASK = 0x1FFFFFFF
    MAX_DATA_LENGTH = 8
    FD_MAX_DATA_LENGTH = 64
    DEFAULT_BAUDRATE = 500000  # 500 kbps - GM standard
    FD_BAUDRATE = 2000000  # 2 Mbps


# =============================================================================
# Timing Constants (milliseconds)
# =============================================================================

class Timing:
    """Timing constants in milliseconds"""
    DEFAULT_TIMEOUT = 1000  # 1 second default
    FLASH_BLOCK_TIMEOUT = 5000  # 5 seconds for flash operations
    DIAGNOSTIC_TIMEOUT = 2000  # 2 seconds for diagnostics
    CONNECT_TIMEOUT = 3000  # 3 seconds for connection
    RETRY_DELAY = 100  # 100ms between retries
    MAX_RETRY_ATTEMPTS = 3


# =============================================================================
# Memory Addresses (GM E37 Platform)
# =============================================================================

class GME37Addresses:
    """Memory addresses for GM E37 platform"""
    FLASH_START = 0x00000000
    FLASH_END = 0x000FFFFF  # 1MB
    CALIBRATION_START = 0x00010000
    CALIBRATION_END = 0x000FFFFF
    VIN_ADDRESS = 0x00010020
    CALIBRATION_ID_ADDRESS = 0x00010040
    CHECKSUM_REGION_START = 0x00010000
    CHECKSUM_REGION_END = 0x000FFFFF
    NUM_CHECKSUMS = 42  # Number of checksums in E37


# =============================================================================
# Device Detection Constants
# =============================================================================

class DeviceDetection:
    """Device detection constants"""
    VID_TOPDON = "VID_1234"  # Replace with actual VID
    PID_RLINK = "PID_5678"  # Replace with actual PID
    VID_FORD = "VID_0403"
    VID_TACTRIX = "VID_1234"


# =============================================================================
# File Extension Constants
# =============================================================================

class Extensions:
    """File extensions"""
    HPT = ".hpt"
    BIN = ".bin"
    HEX = ".hex"
    JSON = ".json"
    XML = ".xml"
    DLL = ".dll"
    LOG = ".log"


# =============================================================================
# Table/Map Constants
# =============================================================================

class Table:
    """Tuning table constants"""
    MAX_ROWS = 32
    MAX_COLS = 32
    SPARK_TABLE_OFFSET = 0x00020000
    FUEL_TABLE_OFFSET = 0x00030000
    VE_TABLE_OFFSET = 0x00040000
    RPM_AXIS_SIZE = 20
    LOAD_AXIS_SIZE = 16


# =============================================================================
# Security/Validation Constants
# =============================================================================

class Validation:
    """Validation constants"""
    MAX_PATH_LENGTH = 260  # Windows MAX_PATH
    MAX_FILENAME_LENGTH = 128
    ALLOWED_PATH_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.\\\\/")
    MIN_CHECKSUM_VALUE = 0x0000
    MAX_CHECKSUM_VALUE = 0xFFFF


# =============================================================================
# Helper Functions
# =============================================================================

def get_flash_size(platform: str) -> int:
    """Get flash size for a platform"""
    sizes = {
        "GM_E37": FlashSize.GM_E37,
        "GM_E38": FlashSize.GM_E38,
        "GM_E39": FlashSize.GM_E39,
        "FORD_PCM": FlashSize.FORD_PCM,
        "FORD_TCM": FlashSize.FORD_TCM,
    }
    return sizes.get(platform.upper(), FlashSize.GM_E37)


def validate_voltage(voltage: float) -> bool:
    """Check if voltage is within safe range for flashing"""
    return Voltage.MIN_BATTERY_FLASH <= voltage <= Voltage.MAX_BATTERY
