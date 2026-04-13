#!/usr/bin/env python3
"""
Checksum Validator for HPT and BIN files
Validates and fixes checksums for various ECM platforms
"""

import struct
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChecksumType(Enum):
    """Types of checksums used in ECMs"""
    CRC32 = "crc32"
    CRC16 = "crc16"
    SUM8 = "sum8"
    SUM16 = "sum16"
    SUM32 = "sum32"
    MD5 = "md5"
    SHA256 = "sha256"
    GM_E37_MAIN = "gm_e37_main"  # GM E37 specific
    GM_E38_MAIN = "gm_e38_main"  # GM E38 specific
    GM_E41_MAIN = "gm_e41_main"  # GM E41 specific


@dataclass
class ChecksumRegion:
    """Defines a memory region with checksum"""
    name: str
    start: int
    end: int
    checksum_type: ChecksumType
    checksum_offset: Optional[int] = None  # Where checksum is stored
    description: str = ""


@dataclass
class ChecksumResult:
    """Result of checksum validation"""
    valid: bool
    region: str
    checksum_type: str
    expected: Union[int, str]
    actual: Union[int, str]
    offset: Optional[int] = None
    error: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report"""
    file_path: str
    platform: str
    overall_valid: bool
    results: List[ChecksumResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ChecksumCalculator:
    """Calculate various checksum types"""
    
    @staticmethod
    def crc32(data: bytes, initial: int = 0) -> int:
        """Calculate CRC32 checksum"""
        import binascii
        return binascii.crc32(data, initial) & 0xFFFFFFFF
    
    @staticmethod
    def crc16(data: bytes, poly: int = 0x1021, initial: int = 0xFFFF) -> int:
        """Calculate CRC16 (CCITT-FALSE)"""
        crc = initial
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
            crc &= 0xFFFF
        return crc
    
    @staticmethod
    def sum8(data: bytes) -> int:
        """Simple 8-bit sum"""
        return sum(data) & 0xFF
    
    @staticmethod
    def sum16(data: bytes) -> int:
        """Simple 16-bit sum"""
        return sum(data) & 0xFFFF
    
    @staticmethod
    def sum32(data: bytes) -> int:
        """Simple 32-bit sum"""
        return sum(data) & 0xFFFFFFFF
    
    @staticmethod
    def md5(data: bytes) -> str:
        """Calculate MD5 hash"""
        return hashlib.md5(data).hexdigest()
    
    @staticmethod
    def sha256(data: bytes) -> str:
        """Calculate SHA256 hash"""
        return hashlib.sha256(data).hexdigest()
    
    @classmethod
    def calculate(cls, data: bytes, checksum_type: ChecksumType) -> Union[int, str]:
        """Calculate checksum based on type"""
        calculators = {
            ChecksumType.CRC32: cls.crc32,
            ChecksumType.CRC16: cls.crc16,
            ChecksumType.SUM8: cls.sum8,
            ChecksumType.SUM16: cls.sum16,
            ChecksumType.SUM32: cls.sum32,
            ChecksumType.MD5: cls.md5,
            ChecksumType.SHA256: cls.sha256,
        }
        
        calc = calculators.get(checksum_type)
        if calc:
            return calc(data)
        
        raise ValueError(f"Unknown checksum type: {checksum_type}")


class PlatformChecksumDB:
    """Database of checksum regions for different platforms"""
    
    # GM E37 (LFX 3.6L V6) checksum regions
    GM_E37_REGIONS = [
        ChecksumRegion(
            name="Main Calibration",
            start=0x00000,
            end=0x80000,
            checksum_type=ChecksumType.CRC32,
            checksum_offset=0x80000,
            description="Main calibration data CRC"
        ),
        ChecksumRegion(
            name="Engine Tables",
            start=0x20000,
            end=0x50000,
            checksum_type=ChecksumType.SUM16,
            checksum_offset=0x50000,
            description="Engine table checksum"
        ),
        ChecksumRegion(
            name="Transmission Tables",
            start=0x50000,
            end=0x60000,
            checksum_type=ChecksumType.SUM16,
            checksum_offset=0x60000,
            description="Transmission table checksum"
        ),
    ]
    
    # GM E38 checksum regions
    GM_E38_REGIONS = [
        ChecksumRegion(
            name="Main Calibration",
            start=0x00000,
            end=0x80000,
            checksum_type=ChecksumType.CRC32,
            checksum_offset=0x80000,
            description="Main calibration data CRC"
        ),
    ]
    
    # GM E41 (Gen V) checksum regions
    GM_E41_REGIONS = [
        ChecksumRegion(
            name="Main Calibration",
            start=0x00000,
            end=0x100000,
            checksum_type=ChecksumType.CRC32,
            checksum_offset=0x100000,
            description="Main calibration data CRC"
        ),
        ChecksumRegion(
            name="Boot Sector",
            start=0x00000,
            end=0x10000,
            checksum_type=ChecksumType.CRC32,
            checksum_offset=0x10000,
            description="Boot sector checksum"
        ),
    ]
    
    PLATFORMS = {
        "GM_E37": GM_E37_REGIONS,
        "GM_E38": GM_E38_REGIONS,
        "GM_E41": GM_E41_REGIONS,
        "GM_E39": GM_E41_REGIONS,  # Same as E41
    }
    
    @classmethod
    def get_regions(cls, platform: str) -> List[ChecksumRegion]:
        """Get checksum regions for a platform"""
        return cls.PLATFORMS.get(platform, [])
    
    @classmethod
    def add_platform(cls, platform: str, regions: List[ChecksumRegion]):
        """Add a new platform definition"""
        cls.PLATFORMS[platform] = regions


class ChecksumValidator:
    """
    Validate and fix checksums in binary and HPT files
    """
    
    def __init__(self, platform: str = "GM_E37"):
        self.platform = platform
        self.regions = PlatformChecksumDB.get_regions(platform)
        self.calculator = ChecksumCalculator()
        
    def validate_binary(self, bin_path: str, 
                       custom_regions: List[ChecksumRegion] = None) -> ValidationReport:
        """
        Validate checksums in a binary file
        
        Args:
            bin_path: Path to binary file
            custom_regions: Optional custom checksum regions
            
        Returns:
            ValidationReport with all results
        """
        regions = custom_regions or self.regions
        report = ValidationReport(
            file_path=bin_path,
            platform=self.platform,
            overall_valid=True
        )
        
        try:
            with open(bin_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            report.errors.append(f"Failed to read file: {e}")
            report.overall_valid = False
            return report
        
        for region in regions:
            result = self._validate_region(data, region)
            report.results.append(result)
            
            if not result.valid:
                report.overall_valid = False
                report.errors.append(
                    f"Checksum mismatch in {region.name}: "
                    f"expected {result.expected}, got {result.actual}"
                )
        
        # Calculate file-level hashes
        report.results.append(ChecksumResult(
            valid=True,
            region="File MD5",
            checksum_type="md5",
            expected="N/A",
            actual=ChecksumCalculator.md5(data)
        ))
        
        report.results.append(ChecksumResult(
            valid=True,
            region="File SHA256",
            checksum_type="sha256",
            expected="N/A",
            actual=ChecksumCalculator.sha256(data)
        ))
        
        logger.info(f"Validated {len(regions)} regions for {bin_path}")
        
        return report
    
    def _validate_region(self, data: bytes, 
                        region: ChecksumRegion) -> ChecksumResult:
        """Validate a single checksum region"""
        try:
            # Extract region data
            region_data = data[region.start:region.end]
            
            if len(region_data) != region.end - region.start:
                return ChecksumResult(
                    valid=False,
                    region=region.name,
                    checksum_type=region.checksum_type.value,
                    expected=0,
                    actual=0,
                    error=f"Region extends beyond file size"
                )
            
            # Calculate actual checksum
            actual_checksum = self.calculator.calculate(
                region_data, 
                region.checksum_type
            )
            
            # Read expected checksum from file
            if region.checksum_offset:
                if region.checksum_type in [ChecksumType.MD5, ChecksumType.SHA256]:
                    # Hash types stored as strings
                    expected_checksum = data[region.checksum_offset:region.checksum_offset + 32].decode('ascii')
                elif region.checksum_type == ChecksumType.CRC32:
                    expected_checksum = struct.unpack_from('<I', data, region.checksum_offset)[0]
                elif region.checksum_type == ChecksumType.CRC16:
                    expected_checksum = struct.unpack_from('<H', data, region.checksum_offset)[0]
                elif region.checksum_type == ChecksumType.SUM32:
                    expected_checksum = struct.unpack_from('<I', data, region.checksum_offset)[0]
                elif region.checksum_type == ChecksumType.SUM16:
                    expected_checksum = struct.unpack_from('<H', data, region.checksum_offset)[0]
                elif region.checksum_type == ChecksumType.SUM8:
                    expected_checksum = struct.unpack_from('B', data, region.checksum_offset)[0]
                else:
                    expected_checksum = 0
            else:
                # No stored checksum, just calculate
                expected_checksum = actual_checksum
            
            return ChecksumResult(
                valid=actual_checksum == expected_checksum,
                region=region.name,
                checksum_type=region.checksum_type.value,
                expected=expected_checksum,
                actual=actual_checksum,
                offset=region.checksum_offset
            )
            
        except Exception as e:
            return ChecksumResult(
                valid=False,
                region=region.name,
                checksum_type=region.checksum_type.value,
                expected=0,
                actual=0,
                error=str(e)
            )
    
    def fix_checksums(self, bin_path: str, output_path: str = None,
                     custom_regions: List[ChecksumRegion] = None) -> ValidationReport:
        """
        Fix all checksums in a binary file
        
        Args:
            bin_path: Input binary file
            output_path: Output file (defaults to overwriting input)
            custom_regions: Optional custom checksum regions
            
        Returns:
            ValidationReport with fix results
        """
        regions = custom_regions or self.regions
        output_path = output_path or bin_path
        
        report = ValidationReport(
            file_path=bin_path,
            platform=self.platform,
            overall_valid=True
        )
        
        try:
            with open(bin_path, 'rb') as f:
                data = bytearray(f.read())
        except Exception as e:
            report.errors.append(f"Failed to read file: {e}")
            report.overall_valid = False
            return report
        
        for region in regions:
            if not region.checksum_offset:
                continue
                
            try:
                # Calculate new checksum
                region_data = data[region.start:region.end]
                new_checksum = self.calculator.calculate(
                    region_data,
                    region.checksum_type
                )
                
                # Write checksum to file
                if region.checksum_type == ChecksumType.CRC32:
                    struct.pack_into('<I', data, region.checksum_offset, new_checksum)
                elif region.checksum_type == ChecksumType.CRC16:
                    struct.pack_into('<H', data, region.checksum_offset, new_checksum)
                elif region.checksum_type == ChecksumType.SUM32:
                    struct.pack_into('<I', data, region.checksum_offset, new_checksum)
                elif region.checksum_type == ChecksumType.SUM16:
                    struct.pack_into('<H', data, region.checksum_offset, new_checksum)
                elif region.checksum_type == ChecksumType.SUM8:
                    data[region.checksum_offset] = new_checksum
                
                report.results.append(ChecksumResult(
                    valid=True,
                    region=region.name,
                    checksum_type=region.checksum_type.value,
                    expected=new_checksum,
                    actual=new_checksum,
                    offset=region.checksum_offset
                ))
                
                logger.info(f"Fixed checksum for {region.name}: 0x{new_checksum:X}")
                
            except Exception as e:
                report.errors.append(f"Failed to fix {region.name}: {e}")
                report.overall_valid = False
        
        # Save fixed file
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)
            logger.info(f"Saved fixed binary: {output_path}")
        except Exception as e:
            report.errors.append(f"Failed to save file: {e}")
            report.overall_valid = False
        
        return report
    
    def validate_hpt(self, hpt_path: str) -> ValidationReport:
        """
        Validate checksums in an HPT file
        
        Extracts binary and validates it
        """
        import tempfile
        from .converter import HPTConverter
        
        converter = HPTConverter()
        
        # Extract binary to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
            tmp_path = tmp.name
        
        try:
            result = converter.hpt_to_bin(hpt_path, tmp_path)
            
            if not result.success:
                report = ValidationReport(
                    file_path=hpt_path,
                    platform=self.platform,
                    overall_valid=False
                )
                report.errors.extend(result.errors)
                return report
            
            # Update platform from HPT
            if result.platform:
                self.platform = result.platform
                self.regions = PlatformChecksumDB.get_regions(self.platform)
            
            # Validate the binary
            report = self.validate_binary(tmp_path)
            report.file_path = hpt_path
            
            return report
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def calculate_file_checksums(self, file_path: str) -> Dict[str, Union[int, str]]:
        """
        Calculate standard checksums for a file
        
        Returns:
            Dict with md5, sha256, crc32, and file size
        """
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return {
            'md5': ChecksumCalculator.md5(data),
            'sha256': ChecksumCalculator.sha256(data),
            'crc32': f"0x{ChecksumCalculator.crc32(data):08X}",
            'size': len(data),
            'size_human': self._human_readable_size(len(data))
        }
    
    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def print_report(self, report: ValidationReport, verbose: bool = False):
        """Print validation report to console"""
        print("\n" + "="*70)
        print("CHECKSUM VALIDATION REPORT")
        print("="*70)
        print(f"File: {report.file_path}")
        print(f"Platform: {report.platform}")
        print(f"Overall: {'[OK] VALID' if report.overall_valid else '[X] INVALID'}")
        print()
        
        print("Region Checksums:")
        print("-"*70)
        for result in report.results:
            status = "[OK]" if result.valid else "[X]"
            print(f"{status} {result.region:30} | {result.checksum_type:10} | ", end="")
            
            if isinstance(result.actual, int):
                print(f"0x{result.actual:08X}", end="")
            else:
                print(f"{result.actual[:16]}...", end="")
            
            if not result.valid:
                print(f" (expected: {result.expected})")
            else:
                print()
        
        if report.errors:
            print("\nErrors:")
            for error in report.errors:
                print(f"  [X] {error}")
        
        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"  [!] {warning}")


class RollingChecksumValidator:
    """
    Validator for rolling/continuous checksums used in some ECMs
    """
    
    def __init__(self, window_size: int = 1024):
        self.window_size = window_size
    
    def calculate_rolling(self, data: bytes, 
                         start_offset: int = 0) -> List[Tuple[int, int]]:
        """
        Calculate rolling checksums over data
        
        Returns:
            List of (offset, checksum) tuples
        """
        results = []
        
        for i in range(0, len(data) - self.window_size, self.window_size):
            chunk = data[i:i + self.window_size]
            checksum = ChecksumCalculator.crc32(chunk)
            results.append((start_offset + i, checksum))
        
        return results
    
    def find_checksum_regions(self, data: bytes, 
                             expected_pattern: bytes) -> List[int]:
        """
        Find potential checksum storage regions by pattern
        
        Args:
            data: Binary data to search
            expected_pattern: Pattern that might indicate checksum storage
            
        Returns:
            List of offsets where pattern was found
        """
        offsets = []
        offset = 0
        
        while True:
            idx = data.find(expected_pattern, offset)
            if idx == -1:
                break
            offsets.append(idx)
            offset = idx + 1
        
        return offsets
