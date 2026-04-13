#!/usr/bin/env python3
"""
HPT Builder - Create and modify HPT files programmatically
"""

import json
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

try:
    from .converter import HPTConverter, HPTHeader
except ImportError:
    from converter import HPTConverter, HPTHeader

logger = logging.getLogger(__name__)


@dataclass
class ModificationRecord:
    """Record of a binary modification"""
    offset: int
    old_value: bytes
    new_value: bytes
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class HPTBuilder:
    """
    Build HPT files from scratch or modify existing ones
    """
    
    def __init__(self, platform: str = "GM_E37", 
                 vin: str = "UNKNOWN",
                 calibration_id: str = "AUTO"):
        self.platform = platform
        self.vin = vin
        self.calibration_id = calibration_id
        
        self.binary_data: Optional[bytes] = None
        self.modifications: List[ModificationRecord] = []
        self.metadata: Dict = {
            "VIN": vin,
            "CalibrationID": calibration_id,
            "Platform": platform,
            "CreatedBy": "HPTBuilder",
            "CreatedAt": datetime.now().isoformat(),
            "History": []
        }
        
    def load_base_binary(self, bin_path: str) -> 'HPTBuilder':
        """Load a base binary file"""
        with open(bin_path, 'rb') as f:
            self.binary_data = f.read()
            
        self.metadata["BinarySize"] = len(self.binary_data)
        self.metadata["BaseFile"] = str(bin_path)
        
        logger.info(f"Loaded base binary: {bin_path} ({len(self.binary_data)} bytes)")
        return self
        
    def load_from_hpt(self, hpt_path: str) -> 'HPTBuilder':
        """Load and extract from existing HPT file"""
        converter = HPTConverter()
        
        # Extract binary
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
            tmp_path = tmp.name
            
        result = converter.hpt_to_bin(hpt_path, tmp_path)
        
        if not result.success:
            raise ValueError(f"Failed to load HPT: {result.errors}")
            
        # Load binary
        self.load_base_binary(tmp_path)
        
        # Load metadata
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w') as tmp:
            json_path = tmp.name
            
        result = converter.hpt_to_json(hpt_path, json_path)
        
        if result.success and result.metadata:
            self.metadata = result.metadata.get('metadata', self.metadata)
            self.platform = result.metadata.get('hpt_info', {}).get('platform', self.platform)
            
        # Cleanup
        Path(tmp_path).unlink()
        Path(json_path).unlink()
        
        logger.info(f"Loaded from HPT: {hpt_path}")
        return self
        
    def modify_bytes(self, offset: int, data: bytes, 
                     description: str = "") -> 'HPTBuilder':
        """
        Modify bytes at specific offset
        
        Args:
            offset: Byte offset in binary
            data: New bytes to write
            description: Description of change
        """
        if self.binary_data is None:
            raise ValueError("No binary loaded. Call load_base_binary() first.")
            
        if offset + len(data) > len(self.binary_data):
            raise ValueError(f"Modification at 0x{offset:X} exceeds binary size")
            
        # Record old value
        old_value = self.binary_data[offset:offset + len(data)]
        
        # Apply modification
        binary_list = bytearray(self.binary_data)
        binary_list[offset:offset + len(data)] = data
        self.binary_data = bytes(binary_list)
        
        # Record modification
        record = ModificationRecord(
            offset=offset,
            old_value=old_value,
            new_value=data,
            description=description
        )
        self.modifications.append(record)
        
        # Update metadata
        self.metadata["History"].append({
            "action": "modify_bytes",
            "offset": f"0x{offset:X}",
            "size": len(data),
            "description": description,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Modified 0x{offset:X}: {old_value.hex()} -> {data.hex()}")
        return self
        
    def patch_table(self, name: str, offset: int, 
                    data: List[List[int]], 
                    row_axis: List[int] = None,
                    col_axis: List[int] = None,
                    description: str = "") -> 'HPTBuilder':
        """
        Patch a 2D table in the binary
        
        Args:
            name: Table name
            offset: Starting offset in binary
            data: 2D array of values
            row_axis: Row axis values
            col_axis: Column axis values
            description: Description of change
        """
        # Flatten 2D data
        flat_data = []
        for row in data:
            flat_data.extend(row)
            
        # Convert to bytes (assuming 16-bit values)
        byte_data = b''.join(struct.pack('<H', int(v)) for v in flat_data)
        
        desc = description or f"Updated {name} table"
        return self.modify_bytes(offset, byte_data, desc)
        
    def set_rev_limit(self, rpm: int, offset: int = 0x20000) -> 'HPTBuilder':
        """
        Set rev limiter RPM
        
        Args:
            rpm: New RPM limit
            offset: Memory offset (platform specific)
        """
        import struct
        rpm_bytes = struct.pack('<H', int(rpm))
        return self.modify_bytes(
            offset, rpm_bytes, 
            f"Set rev limit to {rpm} RPM"
        )
        
    def set_speed_limit(self, mph: int, offset: int = 0x20010) -> 'HPTBuilder':
        """
        Set speed limiter (MPH)
        
        Args:
            mph: New speed limit in MPH
            offset: Memory offset (platform specific)
        """
        import struct
        mph_bytes = struct.pack('<H', int(mph))
        return self.modify_bytes(
            offset, mph_bytes,
            f"Set speed limit to {mph} MPH"
        )
        
    def add_comment(self, comment: str) -> 'HPTBuilder':
        """Add a comment to metadata"""
        if "Comments" not in self.metadata:
            self.metadata["Comments"] = []
            
        if isinstance(self.metadata["Comments"], list):
            self.metadata["Comments"].append({
                "text": comment,
                "timestamp": datetime.now().isoformat()
            })
        else:
            # Convert string to list
            old_comment = self.metadata["Comments"]
            self.metadata["Comments"] = [
                {"text": old_comment, "timestamp": "unknown"},
                {"text": comment, "timestamp": datetime.now().isoformat()}
            ]
            
        return self
        
    def get_modifications_report(self) -> Dict:
        """Get report of all modifications"""
        return {
            "total_modifications": len(self.modifications),
            "modifications": [
                {
                    "offset": f"0x{m.offset:X}",
                    "old": m.old_value.hex(),
                    "new": m.new_value.hex(),
                    "description": m.description,
                    "timestamp": m.timestamp
                }
                for m in self.modifications
            ],
            "metadata": self.metadata
        }
        
    def save(self, output_path: str, 
             compression_level: int = 6,
             fix_checksums: bool = True) -> str:
        """
        Save as HPT file
        
        Args:
            output_path: Path for output .hpt file
            compression_level: Zlib compression level
            fix_checksums: Automatically fix checksums before saving
            
        Returns:
            Path to saved file
        """
        if self.binary_data is None:
            raise ValueError("No binary data to save")
            
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Fix checksums if requested
        binary_data = self.binary_data
        if fix_checksums:
            try:
                try:
                    from .checksum import ChecksumValidator
                except ImportError:
                    from checksum import ChecksumValidator
                
                validator = ChecksumValidator(self.platform)
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
                    tmp_path = tmp.name
                    tmp.write(binary_data)
                
                # Fix checksums
                report = validator.fix_checksums(tmp_path)
                if report.overall_valid or len(report.errors) == 0:
                    with open(tmp_path, 'rb') as f:
                        binary_data = f.read()
                
                Path(tmp_path).unlink()
                logger.info("Checksums fixed automatically")
            except Exception as e:
                logger.warning(f"Could not fix checksums: {e}")
        
        # Update metadata
        self.metadata["BinarySize"] = len(binary_data)
        self.metadata["ModifiedAt"] = datetime.now().isoformat()
        self.metadata["TotalModifications"] = len(self.modifications)
        
        # Serialize metadata
        metadata_json = json.dumps(self.metadata, indent=2)
        metadata_bytes = metadata_json.encode('utf-8')
        
        # Compress binary
        compressed_data = zlib.compress(binary_data, compression_level)
        
        # Build header
        header = HPTHeader(
            platform=self.platform,
            metadata_offset=HPTHeader.HEADER_SIZE,
            binary_offset=HPTHeader.HEADER_SIZE + len(metadata_bytes) + 4,
            binary_size=len(binary_data)
        )
        
        # Assemble file
        import struct
        metadata_length = struct.pack('<I', len(metadata_bytes))
        
        hpt_data = (
            header.to_bytes() + 
            metadata_length + 
            metadata_bytes + 
            compressed_data
        )
        
        # Write file
        with open(output_path, 'wb') as f:
            f.write(hpt_data)
            
        logger.info(f"Saved HPT: {output_path}")
        return str(output_path)
        
    def save_modifications_json(self, output_path: str) -> str:
        """Save modifications report to JSON"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.get_modifications_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        return str(output_path)


# Import struct for patch_table method
import struct
