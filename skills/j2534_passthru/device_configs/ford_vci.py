#!/usr/bin/env python3
"""
Ford VCI (VCM II) Configuration and Support
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FordVCIDevice:
    """Ford VCI (VCM II) Device Support"""
    
    POSSIBLE_DLL_PATHS = [
        r"C:\Program Files\Ford\Ford VCI\j2534\fordvci.dll",
        r"C:\Program Files (x86)\Ford\Ford VCI\j2534\fordvci.dll",
        r"C:\Program Files\Bosch\FordVCI\fordvci.dll",
        r"C:\Program Files (x86)\Bosch\FordVCI\fordvci.dll",
        r"C:\Program Files\Ford Motor Company\VCM II\j2534\vcm2.dll",
        r"C:\Program Files (x86)\Ford Motor Company\VCM II\j2534\vcm2.dll",
        r"C:\Windows\System32\fordvci.dll",
        r"C:\Windows\SysWOW64\fordvci.dll",
    ]
    
    def find_dll(self) -> Optional[str]:
        """Find the Ford VCI J2534 DLL"""
        for path in self.POSSIBLE_DLL_PATHS:
            if Path(path).exists():
                logger.info(f"Found Ford VCI DLL: {path}")
                return path
        return None
        
    def detect_connected(self) -> bool:
        """Check if Ford VCI is connected"""
        import subprocess
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_pnpentity", 
                 "where", "Name like '%VCI%'", "get", "Name"],
                capture_output=True, text=True
            )
            return "VCI" in result.stdout or "VCM" in result.stdout
        except:
            return False
            
    def get_device_info(self) -> Dict:
        """Get device information"""
        return {
            "name": "Ford VCI (VCM II)",
            "manufacturer": "Bosch / Ford",
            "dll_found": self.find_dll() is not None,
            "connected": self.detect_connected(),
        }
