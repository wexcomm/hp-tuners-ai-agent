"""
HPT File Converter
Convert HP Tuners .hpt files to/from .bin, .hex, .json formats
"""

from .converter import HPTConverter, ConversionOptions, ConversionResult
from .builder import HPTBuilder
from .comparator import TuneComparator
from .batch import BatchConverter
from .checksum import (
    ChecksumValidator, 
    ChecksumCalculator, 
    ChecksumRegion,
    ChecksumType,
    ValidationReport,
    PlatformChecksumDB
)

__version__ = "1.0.0"

__all__ = [
    "HPTConverter",
    "ConversionOptions",
    "ConversionResult",
    "HPTBuilder",
    "TuneComparator",
    "BatchConverter",
    "ChecksumValidator",
    "ChecksumCalculator",
    "ChecksumRegion",
    "ChecksumType",
    "ValidationReport",
    "PlatformChecksumDB",
]
