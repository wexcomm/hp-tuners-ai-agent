#!/usr/bin/env python3
"""
Test suite for HPT Converter

Tests HPT file format conversion, header parsing, and metadata extraction.
"""

import sys
import unittest
import json
import zlib
from pathlib import Path
import tempfile
import struct

# Add skills path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "hpt_converter"))

from converter import (
    HPTConverter, 
    HPTHeader, 
    ConversionResult,
    ConversionOptions
)


class TestHPTHeader(unittest.TestCase):
    """Test cases for HPTHeader"""
    
    def test_header_creation(self):
        """Test HPT header creation"""
        header = HPTHeader(
            platform="GM_E37",
            metadata_offset=256,
            binary_offset=512,
            binary_size=1048576
        )
        
        self.assertEqual(header.platform, "GM_E37")
        self.assertEqual(header.metadata_offset, 256)
        self.assertEqual(header.binary_offset, 512)
        self.assertEqual(header.binary_size, 1048576)
        self.assertEqual(header.MAGIC, b'HPTF')
        self.assertEqual(header.VERSION, 1)
        self.assertEqual(header.HEADER_SIZE, 256)
    
    def test_header_to_bytes(self):
        """Test converting header to bytes"""
        header = HPTHeader(
            platform="GM_E37",
            metadata_offset=256,
            binary_offset=512,
            binary_size=1048576
        )
        
        header_bytes = header.to_bytes()
        
        # Should be exactly HEADER_SIZE bytes
        self.assertEqual(len(header_bytes), HPTHeader.HEADER_SIZE)
        
        # Should start with magic header
        self.assertTrue(header_bytes.startswith(HPTHeader.MAGIC))
    
    def test_header_from_bytes(self):
        """Test parsing header from bytes"""
        original = HPTHeader(
            platform="GM_E37",
            metadata_offset=256,
            binary_offset=512,
            binary_size=1048576
        )
        
        header_bytes = original.to_bytes()
        parsed = HPTHeader.from_bytes(header_bytes)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.platform, original.platform)
        self.assertEqual(parsed.metadata_offset, original.metadata_offset)
        self.assertEqual(parsed.binary_offset, original.binary_offset)
        self.assertEqual(parsed.binary_size, original.binary_size)
    
    def test_header_from_invalid_bytes(self):
        """Test parsing header from invalid bytes"""
        # Too short
        result = HPTHeader.from_bytes(b"short")
        self.assertIsNone(result)
        
        # Wrong magic
        wrong_magic = b'XXXX' + b'\x00' * 252
        result = HPTHeader.from_bytes(wrong_magic)
        self.assertIsNone(result)
    
    def test_different_platforms(self):
        """Test headers with different platforms"""
        platforms = ["GM_E37", "GM_E38", "FORD_PCM", "CHRYSLER"]
        
        for platform in platforms:
            header = HPTHeader(platform=platform)
            header_bytes = header.to_bytes()
            parsed = HPTHeader.from_bytes(header_bytes)
            
            self.assertIsNotNone(parsed)
            self.assertEqual(parsed.platform, platform)


class TestHPTConverter(unittest.TestCase):
    """Test cases for HPTConverter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.converter = HPTConverter()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test converter initialization"""
        self.assertIsNotNone(self.converter)
    
    def test_hpt_to_bin_not_found(self):
        """Test conversion with non-existent file"""
        result = self.converter.hpt_to_bin(
            "/nonexistent/file.hpt", 
            str(self.temp_path / "out.bin")
        )
        
        # Should return a result object indicating failure
        self.assertIsInstance(result, ConversionResult)
        self.assertFalse(result.success)
    
    def test_hpt_to_json_not_found(self):
        """Test JSON extraction with non-existent file"""
        result = self.converter.hpt_to_json(
            "/nonexistent/file.hpt",
            str(self.temp_path / "out.json")
        )
        
        self.assertIsInstance(result, ConversionResult)
    
    def test_bin_to_hpt_not_found(self):
        """Test bin to hpt conversion with non-existent file"""
        result = self.converter.bin_to_hpt(
            "/nonexistent/file.bin",
            str(self.temp_path / "out.hpt"),
            platform="GM_E37"
        )
        
        self.assertIsInstance(result, ConversionResult)
        self.assertFalse(result.success)


class TestConversionResult(unittest.TestCase):
    """Test cases for ConversionResult"""
    
    def test_successful_result(self):
        """Test creating a successful result"""
        result = ConversionResult(
            success=True,
            input_file="input.hpt",
            output_file="output.bin",
            format_from="HPT",
            format_to="BIN",
            platform="GM_E37",
            binary_size=1048576
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.input_file, "input.hpt")
        self.assertEqual(result.output_file, "output.bin")
        self.assertEqual(result.platform, "GM_E37")
    
    def test_failed_result(self):
        """Test creating a failed result"""
        result = ConversionResult(
            success=False,
            input_file="input.hpt",
            output_file="output.bin",
            format_from="HPT",
            format_to="BIN"
        )
        
        self.assertFalse(result.success)
    
    def test_result_with_errors(self):
        """Test result with error messages"""
        result = ConversionResult(
            success=False,
            input_file="input.hpt",
            output_file="output.bin",
            format_from="HPT",
            format_to="BIN",
            errors=["File not found", "Invalid format"]
        )
        
        self.assertEqual(len(result.errors), 2)
        self.assertIn("File not found", result.errors)


class TestConversionOptions(unittest.TestCase):
    """Test cases for ConversionOptions"""
    
    def test_default_options(self):
        """Test default conversion options"""
        options = ConversionOptions()
        
        self.assertTrue(options.preserve_metadata)
        self.assertTrue(options.calculate_checksums)
        self.assertTrue(options.verify_integrity)
        self.assertEqual(options.compression_level, 6)
        self.assertTrue(options.include_history)
    
    def test_custom_options(self):
        """Test custom conversion options"""
        options = ConversionOptions(
            compression_level=9,
            verify_integrity=False
        )
        
        self.assertEqual(options.compression_level, 9)
        self.assertFalse(options.verify_integrity)


class TestHPTConstants(unittest.TestCase):
    """Test HPT format constants"""
    
    def test_header_magic(self):
        """Test header magic constant"""
        self.assertEqual(HPTHeader.MAGIC, b'HPTF')
    
    def test_header_version(self):
        """Test header version constant"""
        self.assertEqual(HPTHeader.VERSION, 1)
    
    def test_header_size(self):
        """Test header size constant"""
        self.assertEqual(HPTHeader.HEADER_SIZE, 256)


if __name__ == "__main__":
    unittest.main()
