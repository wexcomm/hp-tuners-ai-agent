"""
J2534 PassThru Skill
Direct vehicle communication via J2534-compliant devices
"""

from .core import J2534PassThru, Protocol, J2534Error
from .flash import FlashManager
from .diagnostics import DiagnosticsManager

__version__ = "1.0.0"

__all__ = [
    "J2534PassThru",
    "Protocol", 
    "J2534Error",
    "FlashManager",
    "DiagnosticsManager",
]
