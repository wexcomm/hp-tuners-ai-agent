#!/usr/bin/env python3
"""
TOPDON RLink X3 Configuration and Support

The RLink X3 is a J2534-1/J2534-2 compliant PassThru device from TOPDON.
It's popular for its affordability and broad vehicle support.
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TopdonRLinkX3Device:
    """
    TOPDON RLink X3 Device Support
    
    Device Info:
    - Manufacturer: TOPDON
    - Model: RLink X3 (Corded)
    - Interface: USB
    - Protocols: J2534-1 and J2534-2
    - Software: TOPDON J2534 Tool (in C:\Program Files\TOPDON)
    """
    
    # Possible installation paths for TOPDON software
    POSSIBLE_INSTALL_PATHS = [
        r"C:\Program Files\TOPDON",
        r"C:\Program Files (x86)\TOPDON",
        r"C:\TOPDON",
    ]
    
    # Possible DLL paths
    POSSIBLE_DLL_PATHS = [
        r"C:\Program Files\TOPDON\J2534\rlinkj2534.dll",
        r"C:\Program Files\TOPDON\Driver\rlinkj2534.dll",
        r"C:\Program Files (x86)\TOPDON\J2534\rlinkj2534.dll",
        r"C:\Program Files (x86)\TOPDON\Driver\rlinkj2534.dll",
        r"C:\Windows\System32\rlinkj2534.dll",
        r"C:\Windows\SysWOW64\rlinkj2534.dll",
        r"C:\Program Files\TOPDON\rlinkj2534.dll",
        # Generic names
        r"C:\Program Files\TOPDON\j2534.dll",
        r"C:\Windows\System32\topdon.dll",
    ]
    
    # Protocol support for RLink X3
    SUPPORTED_PROTOCOLS = {
        "CAN": {
            "id": 5,
            "baud_rates": [125000, 250000, 500000, 1000000],
            "default": 500000,
            "description": "Controller Area Network"
        },
        "ISO15765": {
            "id": 6,
            "baud_rates": [125000, 250000, 500000],
            "default": 500000,
            "description": "CAN-based diagnostics"
        },
        "J1850VPW": {
            "id": 1,
            "baud_rates": [10400],
            "default": 10400,
            "description": "GM/Chrysler single-wire"
        },
        "J1850PWM": {
            "id": 2,
            "baud_rates": [41600],
            "default": 41600,
            "description": "Ford dual-wire"
        },
        "ISO9141": {
            "id": 3,
            "baud_rates": [10400, 4800],
            "default": 10400,
            "description": "Older European/Asian"
        },
        "ISO14230": {
            "id": 4,
            "baud_rates": [10400, 4800],
            "default": 10400,
            "description": "Keyword Protocol 2000"
        },
    }
    
    def __init__(self):
        self.dll_path = None
        self.install_path = None
        
    def find_installation(self) -> Optional[Path]:
        """Find TOPDON software installation"""
        for path in self.POSSIBLE_INSTALL_PATHS:
            p = Path(path)
            if p.exists():
                logger.info(f"Found TOPDON installation: {path}")
                self.install_path = p
                return p
        return None
        
    def find_dll(self) -> Optional[str]:
        """Find the RLink X3 J2534 DLL"""
        # First check in installation directory
        install = self.find_installation()
        if install:
            # Search in installation
            for dll in install.rglob("*.dll"):
                if "j2534" in dll.name.lower() or "rlink" in dll.name.lower():
                    logger.info(f"Found RLink DLL: {dll}")
                    self.dll_path = str(dll)
                    return self.dll_path
        
        # Check standard paths
        for path in self.POSSIBLE_DLL_PATHS:
            if Path(path).exists():
                logger.info(f"Found RLink DLL: {path}")
                self.dll_path = path
                return path
                
        return None
        
    def detect_connected(self) -> bool:
        """Check if RLink X3 is connected to PC"""
        import subprocess
        
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_pnpentity", 
                 "where", "Name like '%RLink%' or Name like '%TOPDON%'", 
                 "get", "Name"],
                capture_output=True, text=True
            )
            return "RLink" in result.stdout or "TOPDON" in result.stdout
        except:
            return False
            
    def get_device_info(self) -> Dict:
        """Get detailed device information"""
        return {
            "name": "TOPDON RLink X3",
            "manufacturer": "TOPDON",
            "model": "RLink X3 (Corded)",
            "interface": "USB",
            "j2534_version": "1.04 / 2.02",
            "install_path": str(self.find_installation()) if self.find_installation() else None,
            "dll_path": self.find_dll(),
            "dll_found": self.find_dll() is not None,
            "connected": self.detect_connected(),
            "protocols": list(self.SUPPORTED_PROTOCOLS.keys()),
        }
        
    def get_flash_config(self, platform: str = "GM_E37") -> Dict:
        """
        Get flash programming configuration for specific platform
        
        RLink X3 has been tested with various GM platforms
        """
        configs = {
            "GM_E37": {
                "programming_voltage": 18000,  # 18V
                "voltage_pin": 13,
                "voltage_delay_ms": 500,
                "connect_timeout_ms": 10000,
                "block_size": 1024,
                "inter_block_delay_ms": 50,
                "baud_rate": 500000,
            },
            "GM_E38": {
                "programming_voltage": 18000,
                "voltage_pin": 13,
                "voltage_delay_ms": 500,
                "connect_timeout_ms": 10000,
                "block_size": 1024,
                "inter_block_delay_ms": 50,
                "baud_rate": 500000,
            },
            "GM_E41": {
                "programming_voltage": 18000,
                "voltage_pin": 13,
                "voltage_delay_ms": 1000,
                "connect_timeout_ms": 15000,
                "block_size": 2048,
                "inter_block_delay_ms": 100,
                "baud_rate": 500000,
            },
        }
        
        return configs.get(platform, configs["GM_E37"])


class TopdonRLinkAnalyzer:
    """Analyze TOPDON RLink installation and configuration"""
    
    @staticmethod
    def analyze():
        """Complete analysis of RLink setup"""
        device = TopdonRLinkX3Device()
        
        print("=" * 70)
        print("TOPDON RLINK X3 ANALYZER")
        print("=" * 70)
        print()
        
        # Installation
        install = device.find_installation()
        if install:
            print(f"Installation found: {install}")
            
            # List contents
            print("\nInstallation contents:")
            for item in install.iterdir():
                print(f"  - {item.name}")
        else:
            print("Installation not found in standard locations")
        print()
        
        # DLL
        dll = device.find_dll()
        if dll:
            print(f"J2534 DLL found: {dll}")
        else:
            print("J2534 DLL not found")
            print("  Checked paths:")
            for path in device.POSSIBLE_DLL_PATHS[:5]:
                print(f"    - {path}")
        print()
        
        # USB connection
        connected = device.detect_connected()
        print(f"Device connected: {'Yes' if connected else 'No'}")
        print()
        
        # Full info
        info = device.get_device_info()
        print("Device Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
            
        return info


# Export for use in J2534PassThru
RLINK_X3_CONFIG = {
    "name": "TOPDON RLink X3",
    "dll_paths": TopdonRLinkX3Device.POSSIBLE_DLL_PATHS,
    "protocols": list(TopdonRLinkX3Device.SUPPORTED_PROTOCOLS.keys()),
    "requires_voltage": True,
    "voltage_pin": 13,
    "max_voltage_mv": 20000,
    "default_baud": 500000,
}


def detect_and_configure() -> Optional[TopdonRLinkX3Device]:
    """Auto-detect and configure RLink X3"""
    device = TopdonRLinkX3Device()
    
    if not device.find_dll():
        logger.warning("RLink X3 DLL not found")
        return None
        
    logger.info(f"RLink X3 detected: {device.dll_path}")
    return device
