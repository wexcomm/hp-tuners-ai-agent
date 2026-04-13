#!/usr/bin/env python3
"""
TOPDON RLink X3 Analyzer
Extracts configuration from TOPDON software installation
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent))

from topdon_rlink import TopdonRLinkX3Device


def analyze_topdon_installation():
    """Analyze complete TOPDON installation"""
    print("=" * 70)
    print("TOPDON RLINK X3 ANALYZER")
    print("=" * 70)
    print()
    
    device = TopdonRLinkX3Device()
    
    # Installation
    print("1. Checking Installation...")
    install = device.find_installation()
    if install:
        print(f"   Found: {install}")
        
        # List subdirectories
        print("   Contents:")
        try:
            for item in install.iterdir():
                if item.is_dir():
                    print(f"     [DIR]  {item.name}")
                else:
                    print(f"     [FILE] {item.name}")
        except PermissionError:
            print("     (Permission denied - run as administrator)")
    else:
        print("   Not found in standard locations")
        print("   Checked:")
        for path in device.POSSIBLE_INSTALL_PATHS:
            print(f"     - {path}")
    print()
    
    # DLL
    print("2. Checking J2534 DLL...")
    dll = device.find_dll()
    if dll:
        print(f"   Found: {dll}")
    else:
        print("   Not found!")
        print("   Searched paths:")
        for path in device.POSSIBLE_DLL_PATHS[:5]:
            exists = "[EXISTS]" if Path(path).exists() else "[MISSING]"
            print(f"     {exists} {path}")
    print()
    
    # USB
    print("3. Checking USB Connection...")
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_pnpentity", 
             "where", "Name like '%RLink%' or Name like '%TOPDON%' or DeviceID like '%VID_%'", 
             "get", "Name,DeviceID,Status", "/format:csv"],
            capture_output=True, text=True
        )
        
        devices = []
        for line in result.stdout.split('\n'):
            if 'RLink' in line or 'TOPDON' in line:
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    devices.append({
                        'name': parts[1] if len(parts) > 1 else 'Unknown',
                        'device_id': parts[2] if len(parts) > 2 else '',
                        'status': parts[3] if len(parts) > 3 else ''
                    })
        
        if devices:
            print("   Devices found:")
            for dev in devices:
                print(f"     - {dev['name']}")
                print(f"       ID: {dev['device_id']}")
                print(f"       Status: {dev['status']}")
        else:
            print("   No RLink devices detected")
            print("   (Device may need to be connected and powered)")
    except Exception as e:
        print(f"   Error checking USB: {e}")
    print()
    
    # Configuration
    print("4. Configuration Summary...")
    info = device.get_device_info()
    for key, value in info.items():
        if isinstance(value, list):
            print(f"   {key}: {', '.join(value)}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # Save config
    output_file = Path("topdon_rlink_config.json")
    with open(output_file, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"Configuration saved to: {output_file.absolute()}")
    print()
    
    # Next steps
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    
    if dll:
        print("""
Your RLink X3 is ready to use! Try these commands:

  python -m skills.j2534_passthru test
  python -m skills.j2534_passthru info
  
Or use the batch file:
  j2534.bat test
""")
    else:
        print("""
DLL not found. Please:
1. Install TOPDON software from: C:\Program Files\TOPDON
2. Connect your RLink X3 device
3. Install drivers if prompted
4. Run this analyzer again
""")
    
    return info


if __name__ == "__main__":
    analyze_topdon_installation()
    print()
    input("Press Enter to exit...")
