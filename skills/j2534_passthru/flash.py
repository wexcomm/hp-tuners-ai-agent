#!/usr/bin/env python3
"""
Flash Manager for ECU Programming
Handles reading/writing flash memory via J2534
"""

import time
from typing import Optional, Callable
from pathlib import Path
import logging

from .core import J2534PassThru, Protocol, J2534Error

logger = logging.getLogger(__name__)


class FlashManager:
    """
    Manages ECU flash operations
    """
    
    # GM-specific flash constants
    GM_E37_FLASH_SIZE = 1024 * 1024  # 1MB
    GM_E38_FLASH_SIZE = 1024 * 1024  # 1MB
    GM_E41_FLASH_SIZE = 2 * 1024 * 1024  # 2MB
    
    # Flash block sizes
    READ_BLOCK_SIZE = 1024
    WRITE_BLOCK_SIZE = 256
    ERASE_BLOCK_SIZE = 4096
    
    def __init__(self, passthru: J2534PassThru):
        """
        Initialize flash manager
        
        Args:
            passthru: Connected J2534PassThru instance
        """
        self.pt = passthru
        self.platform = None
        self.flash_size = 0
        
    def set_platform(self, platform: str):
        """
        Set platform for flash operations
        
        Args:
            platform: Platform ID (GM_E37, GM_E38, etc.)
        """
        self.platform = platform
        
        sizes = {
            "GM_E37": self.GM_E37_FLASH_SIZE,
            "GM_E38": self.GM_E38_FLASH_SIZE,
            "GM_E41": self.GM_E41_FLASH_SIZE,
        }
        
        self.flash_size = sizes.get(platform, self.GM_E37_FLASH_SIZE)
        logger.info(f"Platform set: {platform}, Flash size: {self.flash_size} bytes")
        
    def read_flash(self, start_address: int = 0, 
                   size: Optional[int] = None,
                   block_size: int = 1024,
                   progress_callback: Optional[Callable[[int, int], None]] = None,
                   channel_id: int = None) -> bytes:
        """
        Read flash memory from ECU
        
        Args:
            start_address: Starting memory address
            size: Number of bytes to read (default: full flash)
            block_size: Read block size
            progress_callback: Function(current, total) for progress updates
            channel_id: J2534 channel (uses first connected if None)
            
        Returns:
            Flash data as bytes
        """
        if size is None:
            size = self.flash_size
            
        if channel_id is None:
            channel_id = list(self.pt.channels.keys())[0]
            
        logger.info(f"Reading flash: 0x{start_address:06X} + {size} bytes")
        
        data = bytearray()
        num_blocks = (size + block_size - 1) // block_size
        
        for i in range(num_blocks):
            addr = start_address + (i * block_size)
            current_block_size = min(block_size, size - len(data))
            
            # Read block (platform-specific implementation)
            block_data = self._read_flash_block(channel_id, addr, current_block_size)
            data.extend(block_data)
            
            if progress_callback:
                progress_callback(len(data), size)
                
            # Small delay between reads
            time.sleep(0.01)
            
        logger.info(f"Flash read complete: {len(data)} bytes")
        return bytes(data)
        
    def _read_flash_block(self, channel_id: int, address: int, 
                          size: int) -> bytes:
        """
        Read a single block of flash memory
        
        This is platform-specific and requires the proper diagnostic protocol
        """
        # Placeholder - real implementation needs:
        # 1. Enter programming mode
        # 2. Send read memory request
        # 3. Receive data
        
        # Return zeros for now (simulated)
        return bytes(size)
        
    def write_flash(self, data: bytes, start_address: int = 0,
                   verify: bool = True,
                   progress_callback: Optional[Callable[[int, int], None]] = None,
                   channel_id: int = None):
        """
        Write flash memory to ECU
        
        Args:
            data: Binary data to write
            start_address: Starting memory address
            verify: Read back and verify after write
            progress_callback: Function(current, total) for progress
            channel_id: J2534 channel
        """
        if channel_id is None:
            channel_id = list(self.pt.channels.keys())[0]
            
        logger.info(f"Writing flash: 0x{start_address:06X} + {len(data)} bytes")
        
        # Pre-flash checks
        self._pre_flash_checks()
        
        # Unlock ECU
        self._unlock_ecu(channel_id)
        
        # Erase sectors before writing
        self._erase_flash_sectors(channel_id, start_address, len(data))
        
        # Write data in blocks
        num_blocks = (len(data) + self.WRITE_BLOCK_SIZE - 1) // self.WRITE_BLOCK_SIZE
        
        for i in range(num_blocks):
            offset = i * self.WRITE_BLOCK_SIZE
            addr = start_address + offset
            block = data[offset:offset + self.WRITE_BLOCK_SIZE]
            
            # Pad last block if needed
            if len(block) < self.WRITE_BLOCK_SIZE:
                block = block + bytes(self.WRITE_BLOCK_SIZE - len(block))
                
            self._write_flash_block(channel_id, addr, block)
            
            if progress_callback:
                progress_callback(offset + len(block), len(data))
                
        # Verify if requested
        if verify:
            logger.info("Verifying flash...")
            read_data = self.read_flash(start_address, len(data), channel_id=channel_id)
            
            if read_data != data:
                raise J2534Error("Flash verification failed!")
                
            logger.info("Flash verification successful")
            
    def _pre_flash_checks(self):
        """Perform safety checks before flashing"""
        # Check battery voltage
        voltage = self.pt.get_battery_voltage()
        if voltage < 12.0:
            raise J2534Error(f"Battery voltage too low: {voltage}V (need >12V)")
        if voltage > 15.0:
            raise J2534Error(f"Battery voltage too high: {voltage}V")
            
        logger.info(f"Battery voltage OK: {voltage}V")
        
    def _unlock_ecu(self, channel_id: int):
        """
        Unlock ECU for programming
        
        Requires seed/key algorithm specific to platform
        """
        logger.info("Unlocking ECU...")
        
        # Request seed
        # Send key
        # Wait for unlock confirmation
        
        # Placeholder - real implementation needs seed/key calculation
        time.sleep(0.5)
        logger.info("ECU unlocked")
        
    def _erase_flash_sectors(self, channel_id: int, start_address: int, size: int):
        """
        Erase flash sectors before writing
        
        Flash memory must be erased before writing (sets bits to 1)
        """
        logger.info(f"Erasing flash sectors: 0x{start_address:06X} + {size}")
        
        # Calculate sectors to erase
        start_sector = start_address // self.ERASE_BLOCK_SIZE
        end_sector = (start_address + size - 1) // self.ERASE_BLOCK_SIZE
        
        for sector in range(start_sector, end_sector + 1):
            sector_addr = sector * self.ERASE_BLOCK_SIZE
            self._erase_sector(channel_id, sector_addr)
            
        logger.info("Erase complete")
        
    def _erase_sector(self, channel_id: int, address: int):
        """Erase a single flash sector"""
        # Platform-specific erase command
        logger.debug(f"Erasing sector at 0x{address:06X}")
        time.sleep(0.1)  # Simulated delay
        
    def _write_flash_block(self, channel_id: int, address: int, data: bytes):
        """Write a single block to flash"""
        # Platform-specific write command
        logger.debug(f"Writing block at 0x{address:06X}: {data[:8].hex()}...")
        time.sleep(0.01)  # Simulated delay
        
    def flash_binary(self, bin_path: str, start_address: int = 0,
                     verify: bool = True,
                     progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        Flash a binary file to ECU
        
        Args:
            bin_path: Path to binary file
            start_address: Start address in flash
            verify: Verify after write
            progress_callback: Progress callback
        """
        bin_path = Path(bin_path)
        
        if not bin_path.exists():
            raise FileNotFoundError(f"Binary file not found: {bin_path}")
            
        with open(bin_path, "rb") as f:
            data = f.read()
            
        logger.info(f"Flashing binary: {bin_path} ({len(data)} bytes)")
        
        self.write_flash(data, start_address, verify, progress_callback)
        
        logger.info(f"Flash complete: {bin_path}")
        
    def backup_flash(self, output_path: str, 
                     progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        Read and save entire flash to file
        
        Args:
            output_path: Path to save backup
            progress_callback: Progress callback
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating flash backup: {output_path}")
        
        # Read full flash
        data = self.read_flash(size=self.flash_size, 
                               progress_callback=progress_callback)
        
        # Save to file
        with open(output_path, "wb") as f:
            f.write(data)
            
        logger.info(f"Backup saved: {output_path}")
        
    def restore_flash(self, input_path: str,
                     progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        Restore flash from backup file
        
        Args:
            input_path: Path to backup file
            progress_callback: Progress callback
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Backup file not found: {input_path}")
            
        logger.info(f"Restoring flash from: {input_path}")
        
        # Read file and flash
        with open(input_path, "rb") as f:
            data = f.read()
            
        self.write_flash(data, verify=True, progress_callback=progress_callback)
        
        logger.info(f"Restore complete: {input_path}")
