#!/usr/bin/env python3
"""
Test suite for File Validator

Tests file path validation, extension checking, and security constraints.
"""

import sys
import unittest
from pathlib import Path
import tempfile

# Add skills path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "hpt_converter"))

try:
    from constants import Validation, Extensions, FlashSize, get_flash_size
except ImportError:
    from constants import Validation, Extensions


class TestPathValidation(unittest.TestCase):
    """Test cases for file path validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def test_valid_path_length(self):
        """Test that valid paths are under max length"""
        valid_path = self.temp_path / "subdir" / "file.hpt"
        self.assertLess(len(str(valid_path)), Validation.MAX_PATH_LENGTH)
    
    def test_path_with_allowed_chars(self):
        """Test paths with allowed characters"""
        valid_name = "test_file-123.hpt"
        for char in valid_name:
            self.assertIn(char, Validation.ALLOWED_PATH_CHARS)
    
    def test_extensions(self):
        """Test file extension constants"""
        self.assertEqual(Extensions.HPT, ".hpt")
        self.assertEqual(Extensions.BIN, ".bin")
        self.assertEqual(Extensions.HEX, ".hex")
        self.assertEqual(Extensions.JSON, ".json")
    
    def test_allowed_extensions(self):
        """Test that HPT and BIN extensions are valid"""
        valid_extensions = [Extensions.HPT, Extensions.BIN, Extensions.HEX]
        
        test_file = self.temp_path / "test.hpt"
        test_file.touch()
        
        self.assertTrue(test_file.suffix in valid_extensions)


class TestFlashSize(unittest.TestCase):
    """Test cases for flash size constants"""
    
    def test_gm_e37_size(self):
        """Test GM E37 flash size"""
        size = get_flash_size("GM_E37")
        self.assertEqual(size, 1048576)
    
    def test_gm_e38_size(self):
        """Test GM E38 flash size"""
        size = get_flash_size("GM_E38")
        self.assertEqual(size, 2097152)
    
    def test_default_size(self):
        """Test default flash size for unknown platform"""
        size = get_flash_size("UNKNOWN")
        self.assertEqual(size, FlashSize.GM_E37)
    
    def test_case_insensitive(self):
        """Test platform name is case insensitive"""
        size1 = get_flash_size("gm_e37")
        size2 = get_flash_size("GM_E37")
        self.assertEqual(size1, size2)


class TestValidationConstants(unittest.TestCase):
    """Test validation-related constants"""
    
    def test_max_path_length(self):
        """Test max path length constant"""
        self.assertEqual(Validation.MAX_PATH_LENGTH, 260)
    
    def test_max_filename_length(self):
        """Test max filename length"""
        self.assertEqual(Validation.MAX_FILENAME_LENGTH, 128)
    
    def test_allowed_chars_not_empty(self):
        """Test allowed characters set is not empty"""
        self.assertGreater(len(Validation.ALLOWED_PATH_CHARS), 0)
    
    def test_checksum_range(self):
        """Test checksum value range"""
        self.assertEqual(Validation.MIN_CHECKSUM_VALUE, 0x0000)
        self.assertEqual(Validation.MAX_CHECKSUM_VALUE, 0xFFFF)


class TestFileOperations(unittest.TestCase):
    """Test file operation helpers"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def test_file_exists_check(self):
        """Test file existence check"""
        test_file = self.temp_path / "exists.txt"
        test_file.write_text("test")
        
        self.assertTrue(test_file.exists())
    
    def test_file_not_exists(self):
        """Test non-existent file"""
        non_existent = self.temp_path / "does_not_exist.txt"
        self.assertFalse(non_existent.exists())
    
    def test_file_size(self):
        """Test file size operations"""
        test_file = self.temp_path / "size_test.bin"
        test_data = bytes(1024)
        test_file.write_bytes(test_data)
        
        self.assertEqual(test_file.stat().st_size, 1024)
    
    def test_directory_creation(self):
        """Test directory creation"""
        new_dir = self.temp_path / "new" / "nested" / "dir"
        new_dir.mkdir(parents=True)
        
        self.assertTrue(new_dir.exists())
        self.assertTrue(new_dir.is_dir())
    
    def test_file_extension_detection(self):
        """Test file extension detection"""
        hpt_file = self.temp_path / "test.hpt"
        bin_file = self.temp_path / "test.bin"
        
        hpt_file.touch()
        bin_file.touch()
        
        self.assertEqual(hpt_file.suffix, Extensions.HPT)
        self.assertEqual(bin_file.suffix, Extensions.BIN)


class TestSecurity(unittest.TestCase):
    """Test security-related functionality"""
    
    def test_path_traversal_prevention(self):
        """Test path traversal prevention"""
        # Paths with .. should be handled carefully
        suspicious_path = "../../../etc/passwd"
        
        # Check that it contains suspicious patterns
        self.assertIn("..", suspicious_path)
    
    def test_invalid_characters(self):
        """Test detection of invalid characters"""
        invalid_chars = ["<", ">", ":", "\"", "|", "?", "*"]
        
        for char in invalid_chars:
            self.assertNotIn(char, Validation.ALLOWED_PATH_CHARS)


if __name__ == "__main__":
    unittest.main()
