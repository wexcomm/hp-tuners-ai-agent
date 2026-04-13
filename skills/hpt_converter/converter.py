#!/usr/bin/env python3
"""
HPT File Converter - Core conversion functionality
Handles .hpt <-> .bin/.hex/.json conversions
"""

import struct
import zlib
import json
import binascii
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversionOptions:
    """Options for file conversion"""
    preserve_metadata: bool = True
    calculate_checksums: bool = True
    verify_integrity: bool = True
    compression_level: int = 6
    include_history: bool = True


@dataclass
class ConversionResult:
    """Result of a conversion operation"""
    success: bool
    input_file: str
    output_file: str
    format_from: str
    format_to: str
    platform: Optional[str] = None
    binary_size: int = 0
    metadata: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class HPTHeader:
    """HPT File Header Structure"""
    MAGIC = b'HPTF'
    VERSION = 1
    HEADER_SIZE = 256
    
    def __init__(self, platform: str = "GM_E37", metadata_offset: int = 0, 
                 binary_offset: int = 0, binary_size: int = 0):
        self.platform = platform
        self.metadata_offset = metadata_offset
        self.binary_offset = binary_offset
        self.binary_size = binary_size
        self.created_at = datetime.now().isoformat()
        
    def to_bytes(self) -> bytes:
        """Serialize header to bytes"""
        header = bytearray(self.HEADER_SIZE)
        
        # Magic (bytes 0-3)
        header[0:4] = self.MAGIC
        
        # Version (bytes 4-7)
        struct.pack_into('<I', header, 4, self.VERSION)
        
        # Platform ID (bytes 8-23)
        platform_bytes = self.platform.encode('utf-8')[:16].ljust(16, b'\x00')
        header[8:24] = platform_bytes
        
        # Metadata offset (bytes 24-27)
        struct.pack_into('<I', header, 24, self.metadata_offset)
        
        # Binary offset (bytes 28-31)
        struct.pack_into('<I', header, 28, self.binary_offset)
        
        # Binary size (bytes 32-35)
        struct.pack_into('<I', header, 32, self.binary_size)
        
        # Created timestamp (bytes 36-68)
        timestamp_bytes = self.created_at.encode('utf-8')[:32].ljust(32, b'\x00')
        header[36:68] = timestamp_bytes
        
        return bytes(header)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['HPTHeader']:
        """Parse header from bytes"""
        if len(data) < cls.HEADER_SIZE:
            return None
            
        # Check magic
        if data[0:4] != cls.MAGIC:
            return None
            
        header = cls()
        header.platform = data[8:24].rstrip(b'\x00').decode('utf-8', errors='ignore')
        header.metadata_offset = struct.unpack_from('<I', data, 24)[0]
        header.binary_offset = struct.unpack_from('<I', data, 28)[0]
        header.binary_size = struct.unpack_from('<I', data, 32)[0]
        header.created_at = data[36:68].rstrip(b'\x00').decode('utf-8', errors='ignore')
        
        return header


class HPTConverter:
    """
    Main converter class for HPT file operations
    """
    
    # Platform definitions with expected binary sizes
    PLATFORMS = {
        "GM_E37": {"ecm": "E37", "binary_size": 1024*1024, "description": "LFX 3.6L V6"},
        "GM_E38": {"ecm": "E38", "binary_size": 1024*1024, "description": "LS3/L99 V8"},
        "GM_E67": {"ecm": "E67", "binary_size": 1024*1024, "description": "Corvette E67"},
        "GM_E41": {"ecm": "E41", "binary_size": 2*1024*1024, "description": "Gen V V8"},
        "GM_E39": {"ecm": "E39", "binary_size": 2*1024*1024, "description": "Gen V Truck"},
        "GM_E78": {"ecm": "E78", "binary_size": 1024*1024, "description": "2.0T/2.5L"},
    }
    
    def __init__(self, options: Optional[ConversionOptions] = None):
        self.options = options or ConversionOptions()
        
    def hpt_to_bin(self, input_path: str, output_path: str,
                   platform: Optional[str] = None) -> ConversionResult:
        """
        Extract raw binary from HPT file
        
        Args:
            input_path: Path to .hpt file
            output_path: Path for output .bin file
            platform: Optional platform override
            
        Returns:
            ConversionResult with operation status
        """
        result = ConversionResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            format_from="hpt",
            format_to="bin"
        )
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            if not input_path.exists():
                result.errors.append(f"Input file not found: {input_path}")
                return result
                
            # Read HPT file
            with open(input_path, 'rb') as f:
                hpt_data = f.read()
                
            # Parse header
            header = HPTHeader.from_bytes(hpt_data)
            if not header:
                result.errors.append("Invalid HPT file: bad header")
                return result
                
            result.platform = platform or header.platform
            
            # Extract compressed data
            compressed_data = hpt_data[header.binary_offset:]
            
            # Decompress
            try:
                binary_data = zlib.decompress(compressed_data)
            except zlib.error as e:
                result.errors.append(f"Decompression failed: {e}")
                # Try reading as uncompressed fallback
                binary_data = hpt_data[header.binary_offset:header.binary_offset + header.binary_size]
                result.warnings.append("File may be uncompressed, attempting raw extraction")
                
            # Verify size
            expected_size = self.PLATFORMS.get(result.platform, {}).get('binary_size', 0)
            if expected_size and len(binary_data) != expected_size:
                result.warnings.append(
                    f"Binary size mismatch: got {len(binary_data)}, expected {expected_size}"
                )
                
            # Write binary
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(binary_data)
                
            result.success = True
            result.binary_size = len(binary_data)
            result.metadata = {
                'platform': result.platform,
                'original_size': len(hpt_data),
                'binary_size': len(binary_data),
                'compression_ratio': len(hpt_data) / len(binary_data) if binary_data else 0
            }
            
            logger.info(f"Converted {input_path} -> {output_path} ({len(binary_data)} bytes)")
            
        except Exception as e:
            result.errors.append(f"Conversion failed: {str(e)}")
            logger.error(f"Conversion error: {e}")
            
        return result
        
    def bin_to_hpt(self, input_path: str, output_path: str,
                   vin: str = "UNKNOWN",
                   platform: str = "GM_E37",
                   calibration_id: str = "AUTO",
                   metadata: Optional[Dict] = None) -> ConversionResult:
        """
        Create HPT file from raw binary
        
        Args:
            input_path: Path to .bin file
            output_path: Path for output .hpt file
            vin: Vehicle VIN
            platform: Vehicle platform (GM_E37, GM_E38, etc.)
            calibration_id: Calibration ID
            metadata: Additional metadata dict
            
        Returns:
            ConversionResult with operation status
        """
        result = ConversionResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            format_from="bin",
            format_to="hpt",
            platform=platform
        )
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            if not input_path.exists():
                result.errors.append(f"Input file not found: {input_path}")
                return result
                
            # Read binary
            with open(input_path, 'rb') as f:
                binary_data = f.read()
                
            result.binary_size = len(binary_data)
            
            # Validate size
            expected_size = self.PLATFORMS.get(platform, {}).get('binary_size', 0)
            if expected_size and len(binary_data) != expected_size:
                result.warnings.append(
                    f"Binary size {len(binary_data)} doesn't match expected {expected_size} for {platform}"
                )
                
            # Create metadata
            meta = {
                "VIN": vin,
                "CalibrationID": calibration_id,
                "Platform": platform,
                "ECM": self.PLATFORMS.get(platform, {}).get('ecm', 'Unknown'),
                "CreatedBy": "HPTConverter",
                "CreatedAt": datetime.now().isoformat(),
                "BinarySize": len(binary_data),
                "Comments": metadata.get('comments', '') if metadata else '',
                "History": [
                    {
                        "action": "created_from_bin",
                        "timestamp": datetime.now().isoformat(),
                        "source": str(input_path)
                    }
                ]
            }
            
            if metadata:
                meta.update(metadata)
                
            # Serialize metadata
            metadata_json = json.dumps(meta, indent=2)
            metadata_bytes = metadata_json.encode('utf-8')
            
            # Compress binary
            compressed_data = zlib.compress(binary_data, self.options.compression_level)
            
            # Build header
            header = HPTHeader(
                platform=platform,
                metadata_offset=HPTHeader.HEADER_SIZE,
                binary_offset=HPTHeader.HEADER_SIZE + len(metadata_bytes) + 4,
                binary_size=len(binary_data)
            )
            
            # Assemble file
            # Header + metadata length + metadata + compressed binary
            metadata_length = struct.pack('<I', len(metadata_bytes))
            
            hpt_data = (
                header.to_bytes() + 
                metadata_length + 
                metadata_bytes + 
                compressed_data
            )
            
            # Write file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(hpt_data)
                
            result.success = True
            result.metadata = meta
            
            logger.info(f"Created {output_path} from {input_path}")
            
        except Exception as e:
            result.errors.append(f"Conversion failed: {str(e)}")
            logger.error(f"Conversion error: {e}")
            
        return result
        
    def hpt_to_json(self, input_path: str, output_path: str,
                    extract_binary: bool = False) -> ConversionResult:
        """
        Convert HPT to JSON representation
        
        Args:
            input_path: Path to .hpt file
            output_path: Path for output .json file
            extract_binary: Also extract binary as base64 in JSON
            
        Returns:
            ConversionResult with operation status
        """
        result = ConversionResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            format_from="hpt",
            format_to="json"
        )
        
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            with open(input_path, 'rb') as f:
                hpt_data = f.read()
                
            # Parse header
            header = HPTHeader.from_bytes(hpt_data)
            if not header:
                result.errors.append("Invalid HPT file")
                return result
                
            result.platform = header.platform
            
            # Extract metadata
            metadata_len = struct.unpack_from('<I', hpt_data, HPTHeader.HEADER_SIZE)[0]
            metadata_start = HPTHeader.HEADER_SIZE + 4
            metadata_bytes = hpt_data[metadata_start:metadata_start + metadata_len]
            
            try:
                metadata = json.loads(metadata_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                metadata = {"raw": metadata_bytes.hex()}
                
            # Extract binary
            compressed_data = hpt_data[header.binary_offset:]
            try:
                binary_data = zlib.decompress(compressed_data)
            except zlib.error:
                binary_data = compressed_data
                
            # Build JSON output
            output = {
                "hpt_info": {
                    "platform": header.platform,
                    "version": HPTHeader.VERSION,
                    "created": header.created_at,
                    "original_size": len(hpt_data),
                    "binary_size": len(binary_data)
                },
                "metadata": metadata,
                "binary_info": {
                    "size": len(binary_data),
                    "checksum": binascii.crc32(binary_data) & 0xFFFFFFFF,
                    "md5": self._calculate_md5(binary_data)
                }
            }
            
            if extract_binary:
                output["binary_b64"] = binascii.b2a_base64(binary_data).decode('utf-8')
                
            # Write JSON
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(output, f, indent=2)
                
            result.success = True
            result.metadata = output
            
            logger.info(f"Converted {input_path} -> {output_path}")
            
        except Exception as e:
            result.errors.append(f"Conversion failed: {str(e)}")
            logger.error(f"Conversion error: {e}")
            
        return result
        
    def hpt_to_hex(self, input_path: str, output_path: str,
                   bytes_per_line: int = 16) -> ConversionResult:
        """
        Convert HPT binary to Intel HEX format
        
        Args:
            input_path: Path to .hpt file
            output_path: Path for output .hex file
            bytes_per_line: Bytes per line in HEX output
            
        Returns:
            ConversionResult with operation status
        """
        result = ConversionResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            format_from="hpt",
            format_to="hex"
        )
        
        try:
            # First extract to bin
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
                tmp_path = tmp.name
                
            bin_result = self.hpt_to_bin(input_path, tmp_path)
            if not bin_result.success:
                result.errors.extend(bin_result.errors)
                return result
                
            result.platform = bin_result.platform
            
            # Read binary
            with open(tmp_path, 'rb') as f:
                binary_data = f.read()
                
            # Convert to Intel HEX
            hex_lines = []
            hex_lines.append(":020000040000FA")  # Extended linear address 0x0000
            
            offset = 0
            while offset < len(binary_data):
                chunk = binary_data[offset:offset + bytes_per_line]
                
                # Build data record
                record_len = len(chunk)
                addr = offset & 0xFFFF
                record_type = 0x00  # Data
                
                # Calculate checksum
                data_sum = sum(chunk)
                checksum = (record_len + (addr >> 8) + (addr & 0xFF) + record_type + data_sum) & 0xFF
                checksum = (~checksum + 1) & 0xFF
                
                # Format line
                hex_line = f":{record_len:02X}{addr:04X}{record_type:02X}{chunk.hex().upper()}{checksum:02X}"
                hex_lines.append(hex_line)
                
                offset += bytes_per_line
                
            # End of file record
            hex_lines.append(":00000001FF")
            
            # Write HEX file
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write('\n'.join(hex_lines))
                
            result.success = True
            result.binary_size = len(binary_data)
            
            # Cleanup temp file
            Path(tmp_path).unlink()
            
            logger.info(f"Converted {input_path} -> {output_path}")
            
        except Exception as e:
            result.errors.append(f"Conversion failed: {str(e)}")
            logger.error(f"Conversion error: {e}")
            
        return result
        
    def json_to_hpt(self, input_path: str, output_path: str) -> ConversionResult:
        """
        Create HPT from JSON representation
        
        Args:
            input_path: Path to JSON file (with binary_b64 field)
            output_path: Path for output .hpt file
            
        Returns:
            ConversionResult with operation status
        """
        result = ConversionResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            format_from="json",
            format_to="hpt"
        )
        
        try:
            input_path = Path(input_path)
            
            with open(input_path, 'r') as f:
                data = json.load(f)
                
            # Extract binary from base64
            if 'binary_b64' not in data:
                result.errors.append("JSON missing binary_b64 field")
                return result
                
            binary_data = binascii.a2b_base64(data['binary_b64'])
            
            # Get metadata
            hpt_info = data.get('hpt_info', {})
            metadata = data.get('metadata', {})
            
            platform = hpt_info.get('platform', 'GM_E37')
            vin = metadata.get('VIN', 'UNKNOWN')
            cal_id = metadata.get('CalibrationID', 'AUTO')
            
            result.platform = platform
            
            # Use bin_to_hpt to create file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
                tmp.write(binary_data)
                tmp_path = tmp.name
                
            return self.bin_to_hpt(
                tmp_path, output_path,
                vin=vin,
                platform=platform,
                calibration_id=cal_id,
                metadata=metadata
            )
            
        except Exception as e:
            result.errors.append(f"Conversion failed: {str(e)}")
            logger.error(f"Conversion error: {e}")
            return result
            
    def _calculate_md5(self, data: bytes) -> str:
        """Calculate MD5 hash of data"""
        import hashlib
        return hashlib.md5(data).hexdigest()
        
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platform IDs"""
        return list(self.PLATFORMS.keys())
        
    def get_platform_info(self, platform: str) -> Optional[Dict]:
        """Get information about a specific platform"""
        return self.PLATFORMS.get(platform)
