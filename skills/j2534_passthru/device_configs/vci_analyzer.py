#!/usr/bin/env python3
"""
Ford VCI Manager Analyzer
Extracts configuration and protocol data from Ford VCI Manager installation
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def find_vci_manager_path() -> Optional[Path]:
    """Find Ford VCI Manager installation path"""
    possible_paths = [
        Path(r"C:\Program Files\Ford\Ford VCI"),
        Path(r"C:\Program Files (x86)\Ford\Ford VCI"),
        Path(r"C:\Program Files\Bosch\FordVCI"),
        Path(r"C:\Program Files (x86)\Bosch\FordVCI"),
        Path(r"C:\Program Files\Ford Motor Company\VCM II"),
        Path(r"C:\Program Files (x86)\Ford Motor Company\VCM II"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    return None


def find_dll_files(base_path: Path) -> List[str]:
    """Find all J2534 DLL files"""
    dlls = []
    for dll in base_path.rglob("*.dll"):
        if "j2534" in str(dll).lower() or "vci" in str(dll).lower():
            dlls.append(str(dll))
    return dlls


def find_config_files(base_path: Path) -> List[str]:
    """Find configuration files"""
    configs = []
    for ext in ["*.xml", "*.ini", "*.conf", "*.json"]:
        for file in base_path.rglob(ext):
            configs.append(str(file))
    return configs


def get_usb_devices() -> List[Dict]:
    """Get USB device list"""
    devices = []
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_pnpentity", 
             "get", "Name,DeviceID,Status", "/format:csv"],
            capture_output=True, text=True
        )
        
        for line in result.stdout.split('\n'):
            if 'VCI' in line or 'VCM' in line:
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    devices.append({
                        'name': parts[1] if len(parts) > 1 else 'Unknown',
                        'device_id': parts[2] if len(parts) > 2 else '',
                        'status': parts[3] if len(parts) > 3 else ''
                    })
    except Exception as e:
        print(f"Error getting USB devices: {e}")
        
    return devices


def analyze_vci_installation():
    """Analyze complete VCI Manager installation"""
    print("=" * 70)
    print("FORD VCI MANAGER ANALYZER")
    print("=" * 70)
    print()
    
    # Find installation
    vci_path = find_vci_manager_path()
    
    if vci_path:
        print(f"Found VCI Manager at: {vci_path}")
        print()
        
        # Find DLLs
        print("J2534 DLL Files:")
        dlls = find_dll_files(vci_path)
        for dll in dlls:
            print(f"  - {dll}")
        print()
        
        # Find configs
        print("Configuration Files:")
        configs = find_config_files(vci_path)
        for cfg in configs[:10]:  # Limit output
            print(f"  - {cfg}")
        if len(configs) > 10:
            print(f"  ... and {len(configs) - 10} more")
        print()
    else:
        print("VCI Manager installation not found in standard locations")
        print()
    
    # Check USB devices
    print("USB Devices:")
    devices = get_usb_devices()
    if devices:
        for dev in devices:
            print(f"  - {dev['name']}")
            print(f"    ID: {dev['device_id']}")
            print(f"    Status: {dev['status']}")
    else:
        print("  No VCI devices detected")
    print()
    
    # Generate config
    print("=" * 70)
    print("GENERATED CONFIGURATION")
    print("=" * 70)
    
    config = {
        "vci_manager": {
            "found": vci_path is not None,
            "path": str(vci_path) if vci_path else None,
        },
        "dll_files": dlls if vci_path else [],
        "config_files": configs[:5] if vci_path else [],
        "usb_devices": devices,
        "j2534_config": {
            "device_name": "Ford VCI / VCM II",
            "supported_protocols": ["CAN", "ISO15765", "J1850VPW", "ISO9141", "ISO14230"],
            "default_protocol": "CAN",
            "can_baud_rates": [125000, 250000, 500000, 1000000],
            "requires_programming_voltage": True,
            "voltage_pin": 13,
        }
    }
    
    print(json.dumps(config, indent=2))
    
    # Save to file
    output_file = Path("ford_vci_config.json")
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print()
    print(f"Configuration saved to: {output_file.absolute()}")
    
    return config


def extract_protocol_data():
    """
    Extract protocol-specific data from VCI Manager
    
    This would parse XML/protocol definition files if available
    """
    vci_path = find_vci_manager_path()
    
    if not vci_path:
        print("VCI Manager not found")
        return
        
    # Look for protocol definition files
    protocol_files = list(vci_path.rglob("*protocol*.xml"))
    protocol_files.extend(vci_path.rglob("*can*.xml"))
    
    print("Protocol Definition Files:")
    for f in protocol_files:
        print(f"  - {f}")
        # Could parse these for detailed protocol info


if __name__ == "__main__":
    analyze_vci_installation()
    print()
    input("Press Enter to exit...")
