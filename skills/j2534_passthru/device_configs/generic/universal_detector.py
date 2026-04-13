#!/usr/bin/env python3
"""
Universal J2534 Device Detector

Automatically detects any J2534-compliant device on the system,
including TOPDON, Tactrix, DrewTech, Ford VCI, and generic tools.
"""

import winreg
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class UniversalJ2534Detector:
    """
    Universal detector for any J2534 PassThru device
    """
    
    # Common J2534 DLL names
    DLL_PATTERNS = [
        "rlink*j2534*.dll",
        "topdon*.dll",
        "openport*.dll",
        "op20*.dll",
        "mongoose*.dll",
        "drewtech*.dll",
        "fordvci*.dll",
        "vcm*.dll",
        "vcm2*.dll",
        "gmvci*.dll",
        "mdi*.dll",
        "bosch*.dll",
        "j2534.dll",
        "passthru*.dll",
        "vci*.dll",
    ]
    
    # Common installation paths (limited to prevent long scans)
    SEARCH_PATHS = [
        r"C:\Program Files\TOPDON",
        r"C:\Program Files (x86)\TOPDON",
        r"C:\Program Files\Ford",
        r"C:\Program Files (x86)\Ford",
        r"C:\Program Files\Tactrix",
        r"C:\Program Files (x86)\Tactrix",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
    ]
    
    # Registry locations
    REGISTRY_PATHS = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\J2534"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\PassThru"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\J2534"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\PassThru"),
    ]
    
    def __init__(self):
        self.found_dlls = []
        self.found_devices = []
        
    def scan_system(self) -> List[Dict]:
        """
        Complete system scan for J2534 devices
        
        Returns:
            List of found device dictionaries
        """
        devices = []
        
        # 1. Check registry first
        reg_devices = self._scan_registry()
        devices.extend(reg_devices)
        
        # 2. Scan common paths
        path_devices = self._scan_common_paths()
        devices.extend(path_devices)
        
        # 3. Check known device configs
        known_devices = self._check_known_devices()
        devices.extend(known_devices)
        
        # Remove duplicates
        seen = set()
        unique_devices = []
        for dev in devices:
            key = dev.get('dll_path', dev.get('name', ''))
            if key and key not in seen:
                seen.add(key)
                unique_devices.append(dev)
        
        self.found_devices = unique_devices
        return unique_devices
        
    def _scan_registry(self) -> List[Dict]:
        """Scan Windows Registry for J2534 entries"""
        devices = []
        
        for hkey, path in self.REGISTRY_PATHS:
            try:
                key = winreg.OpenKey(hkey, path)
                
                # Enumerate subkeys (device entries)
                try:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey_path = f"{path}\\{subkey_name}"
                            
                            device_info = self._read_device_from_registry(hkey, subkey_path)
                            if device_info:
                                devices.append(device_info)
                            
                            i += 1
                        except OSError:
                            break
                except:
                    pass
                
                winreg.CloseKey(key)
            except:
                pass
        
        return devices
        
    def _read_device_from_registry(self, hkey, path: str) -> Optional[Dict]:
        """Read device info from registry"""
        try:
            key = winreg.OpenKey(hkey, path)
            
            info = {
                "source": "registry",
                "registry_path": path,
            }
            
            # Try to read common values
            try:
                name = winreg.QueryValueEx(key, "Name")[0]
                info["name"] = name
            except:
                pass
            
            try:
                dll_path = winreg.QueryValueEx(key, "FunctionLibrary")[0]
                info["dll_path"] = dll_path
            except:
                try:
                    dll_path = winreg.QueryValueEx(key, "DllPath")[0]
                    info["dll_path"] = dll_path
                except:
                    pass
            
            try:
                vendor = winreg.QueryValueEx(key, "Vendor")[0]
                info["vendor"] = vendor
            except:
                pass
            
            winreg.CloseKey(key)
            
            return info if "dll_path" in info else None
            
        except:
            return None
        
    def _scan_common_paths(self) -> List[Dict]:
        """Scan common installation paths for J2534 DLLs"""
        devices = []
        
        for base_path in self.SEARCH_PATHS:
            base = Path(base_path)
            if not base.exists():
                continue
            
            # Search for DLLs
            for pattern in self.DLL_PATTERNS:
                for dll_path in base.rglob(pattern):
                    if dll_path.is_file():
                        device_info = {
                            "source": "file_scan",
                            "name": dll_path.stem,
                            "dll_path": str(dll_path),
                            "vendor": self._guess_vendor(dll_path.name),
                        }
                        devices.append(device_info)
        
        return devices
        
    def _check_known_devices(self) -> List[Dict]:
        """Check for known device configurations"""
        devices = []
        
        # Try to import and check each known device type
        try:
            from ..topdon_rlink import TopdonRLinkX3Device
            rlink = TopdonRLinkX3Device()
            if rlink.find_dll():
                devices.append({
                    "name": "TOPDON RLink X3",
                    "type": "known",
                    "dll_path": rlink.find_dll(),
                    "vendor": "TOPDON",
                })
        except:
            pass
        
        try:
            from ..ford_vci import FordVCIDevice
            ford = FordVCIDevice()
            if ford.find_dll():
                devices.append({
                    "name": "Ford VCI / VCM II",
                    "type": "known",
                    "dll_path": ford.find_dll(),
                    "vendor": "Bosch / Ford",
                })
        except:
            pass
        
        return devices
        
    def _guess_vendor(self, dll_name: str) -> str:
        """Guess vendor from DLL name"""
        name_lower = dll_name.lower()
        
        vendors = {
            "rlink": "TOPDON",
            "topdon": "TOPDON",
            "openport": "Tactrix",
            "op20": "Tactrix",
            "mongoose": "DrewTech",
            "drewtech": "DrewTech",
            "ford": "Ford / Bosch",
            "vcm": "Ford / Bosch",
            "gm": "General Motors",
            "mdi": "General Motors",
            "bosch": "Bosch",
        }
        
        for key, vendor in vendors.items():
            if key in name_lower:
                return vendor
        
        return "Unknown"
        
    def get_best_device(self) -> Optional[Dict]:
        """
        Get the best/most likely device to use
        
        Returns:
            Device dictionary or None
        """
        devices = self.scan_system()
        
        if not devices:
            return None
        
        # Prefer devices from registry (more reliable)
        registry_devices = [d for d in devices if d.get("source") == "registry"]
        if registry_devices:
            return registry_devices[0]
        
        # Then known devices
        known_devices = [d for d in devices if d.get("type") == "known"]
        if known_devices:
            return known_devices[0]
        
        # Fall back to first found
        return devices[0]
        
    def print_summary(self):
        """Print summary of found devices"""
        devices = self.scan_system()
        
        print("=" * 70)
        print("J2534 DEVICE DETECTION SUMMARY")
        print("=" * 70)
        print()
        
        if not devices:
            print("No J2534 devices found!")
            print()
            print("Please:")
            print("  1. Install your J2534 device drivers")
            print("  2. Connect the device via USB")
            print("  3. Run this detector again")
            return
        
        print(f"Found {len(devices)} J2534 device(s):\n")
        
        for i, dev in enumerate(devices, 1):
            print(f"{i}. {dev.get('name', 'Unknown Device')}")
            print(f"   Vendor: {dev.get('vendor', 'Unknown')}")
            print(f"   Source: {dev.get('source', 'Unknown')}")
            if 'dll_path' in dev:
                print(f"   DLL: {dev['dll_path']}")
            print()
        
        best = self.get_best_device()
        if best:
            print("Recommended device:")
            print(f"  {best.get('name', 'Unknown')}")
            print(f"  DLL: {best.get('dll_path', 'Not found')}")


def detect_any_device() -> Optional[Dict]:
    """
    Convenience function to detect any J2534 device
    
    Returns:
        Best device dictionary or None
    """
    detector = UniversalJ2534Detector()
    return detector.get_best_device()


if __name__ == "__main__":
    detector = UniversalJ2534Detector()
    detector.print_summary()
    
    print()
    input("Press Enter to exit...")
