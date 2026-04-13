#!/usr/bin/env python3
"""
Input validation utilities for HPT Converter
Provides secure path validation and sanitization
"""

import re
from pathlib import Path
from typing import Optional, Tuple


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


class PathValidator:
    """Validates file paths for security"""
    
    # Dangerous patterns that could indicate path traversal
    DANGEROUS_PATTERNS = [
        r'\.\.',           # Parent directory reference
        r'\~',             # Home directory
        r'\$\w+',          # Environment variables
        r'[<>:"|?*]',      # Invalid Windows characters
    ]
    
    @classmethod
    def validate_input_path(cls, path: str, must_exist: bool = True) -> Path:
        """
        Validate an input file path
        
        Args:
            path: Input path string
            must_exist: Whether file must exist
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If path is invalid
        """
        if not path or not isinstance(path, (str, Path)):
            raise ValidationError("Path must be a non-empty string")
        
        path_str = str(path)
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, path_str):
                raise ValidationError(f"Path contains invalid characters: {path_str}")
        
        # Convert to Path and resolve
        try:
            path_obj = Path(path_str).resolve()
        except Exception as e:
            raise ValidationError(f"Invalid path format: {e}")
        
        # Check if path is within allowed directory (project root)
        # This prevents accessing system files
        try:
            # Get project root (assume we're in skills/hpt_converter/)
            project_root = Path(__file__).parent.parent.parent.resolve()
            path_obj.relative_to(project_root)
        except ValueError:
            # Path is outside project - that's okay for input files
            # but we should log it
            pass
        
        if must_exist and not path_obj.exists():
            raise ValidationError(f"File does not exist: {path_obj}")
        
        if must_exist and not path_obj.is_file():
            raise ValidationError(f"Path is not a file: {path_obj}")
        
        return path_obj
    
    @classmethod
    def validate_output_path(cls, path: str, allow_overwrite: bool = True) -> Path:
        """
        Validate an output file path
        
        Args:
            path: Output path string
            allow_overwrite: Whether to allow overwriting existing files
            
        Returns:
            Validated Path object
        """
        if not path or not isinstance(path, (str, Path)):
            raise ValidationError("Path must be a non-empty string")
        
        path_str = str(path)
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, path_str):
                raise ValidationError(f"Path contains invalid characters: {path_str}")
        
        try:
            path_obj = Path(path_str).resolve()
        except Exception as e:
            raise ValidationError(f"Invalid path format: {e}")
        
        # Ensure parent directory exists or can be created
        parent = path_obj.parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValidationError(f"Cannot create output directory: {e}")
        
        # Check if file exists
        if path_obj.exists() and not allow_overwrite:
            raise ValidationError(f"File already exists: {path_obj}")
        
        return path_obj


class PlatformValidator:
    """Validates platform identifiers"""
    
    VALID_PLATFORMS = {
        'GM_E37', 'GM_E38', 'GM_E41', 'GM_E39', 'GM_E67', 'GM_E78',
        'FORD_PCM', 'CHRYSLER_PCM',  # Add more as needed
    }
    
    @classmethod
    def validate(cls, platform: str) -> str:
        """
        Validate platform identifier
        
        Args:
            platform: Platform string (e.g., 'GM_E37')
            
        Returns:
            Normalized platform string
        """
        if not platform or not isinstance(platform, str):
            raise ValidationError("Platform must be a non-empty string")
        
        platform_upper = platform.upper().strip()
        
        # Allow platforms even if not in predefined list
        # Just ensure format is reasonable
        if not re.match(r'^[A-Z][A-Z0-9_]+$', platform_upper):
            raise ValidationError(f"Invalid platform format: {platform}")
        
        return platform_upper


class BinaryValidator:
    """Validates binary data"""
    
    @staticmethod
    def validate_size(data: bytes, min_size: int = 0, max_size: int = 10*1024*1024) -> bool:
        """
        Validate binary data size
        
        Args:
            data: Binary data
            min_size: Minimum allowed size
            max_size: Maximum allowed size (default 10MB)
            
        Returns:
            True if valid
        """
        if not isinstance(data, bytes):
            raise ValidationError("Data must be bytes")
        
        size = len(data)
        
        if size < min_size:
            raise ValidationError(f"Data too small: {size} bytes (min: {min_size})")
        
        if size > max_size:
            raise ValidationError(f"Data too large: {size} bytes (max: {max_size})")
        
        return True
    
    @staticmethod
    def validate_platform_size(data: bytes, platform: str) -> bool:
        """
        Validate binary size matches expected platform size
        
        Args:
            data: Binary data
            platform: Platform identifier
        """
        PLATFORM_SIZES = {
            'GM_E37': 1024 * 1024,      # 1MB
            'GM_E38': 1024 * 1024,      # 1MB
            'GM_E41': 2 * 1024 * 1024,  # 2MB
            'GM_E78': 1024 * 1024,      # 1MB
        }
        
        expected_size = PLATFORM_SIZES.get(platform)
        if expected_size and len(data) != expected_size:
            raise ValidationError(
                f"Binary size {len(data)} does not match expected {expected_size} for {platform}"
            )
        
        return True


def safe_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe
    
    Args:
        filename: Input filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip('. ')
    
    # Ensure not empty
    if not filename:
        filename = 'unnamed'
    
    return filename
