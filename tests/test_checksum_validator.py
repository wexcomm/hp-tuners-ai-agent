#!/usr/bin/env python3
"""
Test suite for ChecksumValidator

Tests checksum calculation, validation, and fixing functionality.
"""

import sys
import unittest
from pathlib import Path
import tempfile

# Add skills path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "hpt_converter"))

from checksum import (
    ChecksumValidator, 
    ChecksumCalculator,
    ChecksumRegion,
    ChecksumResult,
    ValidationReport,
    ChecksumType
)


class TestChecksumCalculator(unittest.TestCase):
    """Test cases for ChecksumCalculator"""
    
    def test_crc32_basic(self):
        """Test basic CRC32 calculation"""
        test_data = b"hello"
        crc = ChecksumCalculator.crc32(test_data)
        
        # CRC32 should be a positive integer
        self.assertIsInstance(crc, int)
        self.assertGreaterEqual(crc, 0)
    
    def test_crc32_consistency(self):
        """Test that CRC32 is consistent"""
        test_data = b"test data"
        crc1 = ChecksumCalculator.crc32(test_data)
        crc2 = ChecksumCalculator.crc32(test_data)
        self.assertEqual(crc1, crc2)
    
    def test_crc16_basic(self):
        """Test basic CRC16 calculation"""
        test_data = b"hello"
        crc = ChecksumCalculator.crc16(test_data)
        
        # CRC16 should be 16-bit (0-65535)
        self.assertIsInstance(crc, int)
        self.assertGreaterEqual(crc, 0)
        self.assertLessEqual(crc, 0xFFFF)
    
    def test_sum8_basic(self):
        """Test 8-bit sum calculation"""
        test_data = bytes([0x01, 0x02, 0x03, 0x04])
        result = ChecksumCalculator.sum8(test_data)
        
        # Should be sum mod 256
        expected = (0x01 + 0x02 + 0x03 + 0x04) & 0xFF
        self.assertEqual(result, expected)
    
    def test_sum16_basic(self):
        """Test 16-bit sum calculation"""
        test_data = bytes([0x01, 0x02] * 100)
        result = ChecksumCalculator.sum16(test_data)
        
        # Should be 16-bit value
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 0xFFFF)


class TestChecksumTypes(unittest.TestCase):
    """Test checksum type enum"""
    
    def test_enum_values(self):
        """Test that all expected types exist"""
        self.assertEqual(ChecksumType.CRC32.value, "crc32")
        self.assertEqual(ChecksumType.CRC16.value, "crc16")
        self.assertEqual(ChecksumType.SUM8.value, "sum8")
        self.assertEqual(ChecksumType.SUM16.value, "sum16")
        self.assertEqual(ChecksumType.MD5.value, "md5")
        self.assertEqual(ChecksumType.SHA256.value, "sha256")
    
    def test_gm_platform_types(self):
        """Test GM platform-specific types"""
        self.assertEqual(ChecksumType.GM_E37_MAIN.value, "gm_e37_main")
        self.assertEqual(ChecksumType.GM_E38_MAIN.value, "gm_e38_main")


class TestValidationReport(unittest.TestCase):
    """Test cases for ValidationReport"""
    
    def test_report_creation(self):
        """Test creating a validation report"""
        report = ValidationReport(
            file_path="test.bin",
            platform="GM_E37",
            overall_valid=True
        )
        
        self.assertEqual(report.file_path, "test.bin")
        self.assertEqual(report.platform, "GM_E37")
        self.assertTrue(report.overall_valid)
        self.assertEqual(len(report.results), 0)
        self.assertEqual(len(report.errors), 0)
    
    def test_report_with_results(self):
        """Test report with checksum results"""
        result = ChecksumResult(
            valid=True,
            region="main",
            checksum_type="crc32",
            expected=0x1234,
            actual=0x1234
        )
        
        report = ValidationReport(
            file_path="test.bin",
            platform="GM_E37",
            overall_valid=True,
            results=[result]
        )
        
        self.assertEqual(len(report.results), 1)
        self.assertTrue(report.results[0].valid)


class TestChecksumRegion(unittest.TestCase):
    """Test cases for ChecksumRegion"""
    
    def test_region_creation(self):
        """Test creating a checksum region"""
        region = ChecksumRegion(
            name="main_checksum",
            start=0x10000,
            end=0xFFFFF,
            checksum_type=ChecksumType.GM_E37_MAIN,
            description="Main firmware region"
        )
        
        self.assertEqual(region.name, "main_checksum")
        self.assertEqual(region.start, 0x10000)
        self.assertEqual(region.end, 0xFFFFF)
        self.assertEqual(region.checksum_type, ChecksumType.GM_E37_MAIN)


class TestChecksumValidator(unittest.TestCase):
    """Test cases for ChecksumValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ChecksumValidator("GM_E37")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test validator initialization"""
        self.assertEqual(self.validator.platform, "GM_E37")
    
    def test_different_platforms(self):
        """Test initialization with different platforms"""
        validator_e38 = ChecksumValidator("GM_E38")
        self.assertEqual(validator_e38.platform, "GM_E38")


if __name__ == "__main__":
    unittest.main()
