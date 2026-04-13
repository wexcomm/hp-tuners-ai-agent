"""
Generic Diagnostic Tool Support

Auto-detects and configures any J2534-compliant diagnostic tool
"""

from .universal_detector import UniversalJ2534Detector, detect_any_device

__all__ = ['UniversalJ2534Detector', 'detect_any_device']
