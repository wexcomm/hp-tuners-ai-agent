#!/usr/bin/env python3
"""
Generic Diagnostic Tool Analyzer

Analyzes any J2534-based diagnostic software to extract:
- DLL paths and configurations
- Protocol definitions
- Supported vehicles
- Communication parameters

Works with:
- Generic Diagnostic Tool
- Any J2534 PassThru application
- OEM dealer tools (Ford IDS, GM GDS2, etc.)
- Third-party tuning software
"""

import json
import subprocess
import winreg
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys


def find_shortcut_target(shortcut_path: str) -> Optional[str]:
    """
    Resolve a Windows shortcut (.lnk) to its target
    
    Args:
        shortcut_path: Path to .lnk file
        
    Returns:
        Target path or None
    """
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        return shortcut.Targetpath
    except ImportError:
        print("Note: win32com not available, cannot resolve shortcut")
        return None
    except Exception as e:
        print(f"Error resolving shortcut: {e}")
        return None


def analyze_diagnostic_tool(tool_path: str) -> Dict:
    """
    Analyze a diagnostic tool installation
    
    Args:
        tool_path: Path to tool executable or installation directory
        
    Returns:
        Dictionary with tool information
    """
    path = Path(tool_path)
    
    # If it's a file, get the directory
    if path.is_file():
        install_dir = path.parent
        exe_path = path
    else:
        install_dir = path
        # Find main executable
        exe_path = None
        for exe in path.glob("*.exe"):
            exe_path = exe
            break
    
    print(f"Analyzing: {install_dir}")
    print()
    
    info = {
        "name": install_dir.name,
        "path": str(install_dir),
        "executable": str(exe_path) if exe_path else None,
        "exists": install_dir.exists(),
    }
    
    if not install_dir.exists():
        return info
    
    # Find J2534 DLLs
    print("Searching for J2534 DLLs...")
    dlls = find_j2534_dlls(install_dir)
    info["j2534_dlls"] = dlls
    
    if dlls:
        print(f"  Found {len(dlls)} J2534 DLL(s):")
        for dll in dlls:
            print(f"    - {dll}")
    else:
        print("  No J2534 DLLs found in tool directory")
    print()
    
    # Find configuration files
    print("Searching for configuration files...")
    configs = find_config_files(install_dir)
    info["config_files"] = configs
    
    print(f"  Found {len(configs)} configuration file(s)")
    for cfg in configs[:10]:  # Show first 10
        print(f"    - {cfg.name}")
    if len(configs) > 10:
        print(f"    ... and {len(configs) - 10} more")
    print()
    
    # Find protocol definitions
    print("Searching for protocol definitions...")
    protocols = find_protocol_files(install_dir)
    info["protocol_files"] = protocols
    print(f"  Found {len(protocols)} protocol file(s)")
    print()
    
    # Analyze registry entries
    print("Checking Windows Registry...")
    registry_info = check_registry(install_dir.name)
    info["registry"] = registry_info
    print()
    
    # Check for vehicle databases
    print("Searching for vehicle databases...")
    vehicle_dbs = find_vehicle_databases(install_dir)
    info["vehicle_databases"] = vehicle_dbs
    print(f"  Found {len(vehicle_dbs)} database file(s)")
    print()
    
    return info


def find_j2534_dlls(directory: Path) -> List[str]:
    """Find all J2534-related DLL files"""
    dlls = []
    
    if not directory.exists():
        return dlls
    
    for dll in directory.rglob("*.dll"):
        name_lower = dll.name.lower()
        # Common J2534 DLL patterns
        if any(pattern in name_lower for pattern in [
            "j2534", "passthru", "vci", "vcm", "rlink", 
            "op20", "mongoose", "drewtech", "ford", "gm"
        ]):
            dlls.append(str(dll))
    
    return dlls


def find_config_files(directory: Path) -> List[Path]:
    """Find configuration files"""
    configs = []
    
    if not directory.exists():
        return configs
    
    patterns = ["*.xml", "*.ini", "*.conf", "*.cfg", "*.json", "*.yaml", "*.yml"]
    
    for pattern in patterns:
        for file in directory.rglob(pattern):
            # Filter out common non-config files
            if file.name.lower() not in ['manifest.json', 'package.json']:
                configs.append(file)
    
    return configs


def find_protocol_files(directory: Path) -> List[Path]:
    """Find protocol definition files"""
    protocols = []
    
    if not directory.exists():
        return protocols
    
    # Look for protocol-related files
    keywords = ["protocol", "can", "kwp", "iso", "j1850", "obd"]
    
    for file in directory.rglob("*"):
        if file.is_file():
            name_lower = file.name.lower()
            if any(kw in name_lower for kw in keywords):
                protocols.append(file)
    
    return protocols


def find_vehicle_databases(directory: Path) -> List[Path]:
    """Find vehicle database files"""
    dbs = []
    
    if not directory.exists():
        return dbs
    
    # Common database extensions and patterns
    patterns = ["*.mdb", "*.accdb", "*.sqlite", "*.db", "*.sdf"]
    keywords = ["vehicle", "ecu", "calibration", "vin"]
    
    for pattern in patterns:
        for file in directory.rglob(pattern):
            dbs.append(file)
    
    # Also check for files with vehicle-related names
    for file in directory.rglob("*"):
        if file.is_file():
            name_lower = file.name.lower()
            if any(kw in name_lower for kw in keywords):
                if file not in dbs:
                    dbs.append(file)
    
    return dbs


def check_registry(software_name: str) -> Dict:
    """Check Windows Registry for software entries"""
    registry_info = {
        "entries_found": [],
        "j2534_entries": []
    }
    
    # Common registry paths
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\" + software_name),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\" + software_name),
        (winreg.HKEY_CURRENT_USER, "SOFTWARE\\" + software_name),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\J2534"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\PassThru"),
    ]
    
    for hkey, path in registry_paths:
        try:
            key = winreg.OpenKey(hkey, path)
            registry_info["entries_found"].append(path)
            
            # Try to read values
            try:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        if "dll" in name.lower() or "path" in name.lower():
                            registry_info["j2534_entries"].append({
                                "key": path,
                                "name": name,
                                "value": str(value)
                            })
                        i += 1
                    except OSError:
                        break
            except:
                pass
            
            winreg.CloseKey(key)
        except:
            pass
    
    return registry_info


def extract_j2534_info_from_dll(dll_path: str) -> Dict:
    """
    Try to extract information from a J2534 DLL
    
    This would use Windows API to query DLL exports
    """
    info = {
        "path": dll_path,
        "exists": Path(dll_path).exists(),
        "exports": []
    }
    
    if not info["exists"]:
        return info
    
    # Common J2534 API functions
    j2534_exports = [
        "PassThruOpen",
        "PassThruClose",
        "PassThruConnect",
        "PassThruDisconnect",
        "PassThruReadMsgs",
        "PassThruWriteMsgs",
        "PassThruStartPeriodicMsg",
        "PassThruStopPeriodicMsg",
        "PassThruReadVersion",
        "PassThruGetLastError",
        "PassThruIoctl"
    ]
    
    # Note: Actually checking exports requires pefile or similar library
    # For now, just list what we expect
    info["expected_exports"] = j2534_exports
    
    return info


def analyze_all_tools():
    """Analyze all known diagnostic tools on the system"""
    print("=" * 70)
    print("GENERIC DIAGNOSTIC TOOL ANALYZER")
    print("=" * 70)
    print()
    
    # Known diagnostic tool paths to check
    known_tools = [
        # User's tools
        ("TOPDON RLink", r"C:\Program Files\TOPDON"),
        ("Ford VCI", r"C:\Program Files\Ford\Ford VCI"),
        ("Generic Diagnostic", r"C:\Program Files\Generic Diagnostic Tool"),
        
        # Common tools
        ("Tactrix", r"C:\Program Files\Tactrix"),
        ("DrewTech", r"C:\Program Files\Drew Technologies"),
        ("HP Tuners", r"C:\Program Files\HP Tuners"),
        ("EFI Live", r"C:\Program Files\EFILive"),
        ("TunerCat", r"C:\Program Files\TunerCat"),
        
        # OEM Tools
        ("Ford IDS", r"C:\Program Files\Ford Motor Company"),
        ("GM GDS2", r"C:\Program Files\General Motors"),
        ("Chrysler wiTECH", r"C:\Program Files\wiTECH"),
    ]
    
    found_tools = []
    
    for name, path in known_tools:
        p = Path(path)
        if p.exists():
            print(f"Found: {name}")
            found_tools.append((name, path))
    
    if not found_tools:
        print("No known diagnostic tools found in standard locations")
    
    print()
    return found_tools


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze diagnostic tool installations'
    )
    parser.add_argument('--tool-path', '-t', 
                       help='Path to diagnostic tool or shortcut')
    parser.add_argument('--scan-all', '-a', action='store_true',
                       help='Scan for all known tools')
    
    args = parser.parse_args()
    
    results = {}
    
    if args.scan_all:
        found = analyze_all_tools()
        for name, path in found:
            print(f"\n{'='*70}")
            print(f"Analyzing: {name}")
            print('='*70)
            results[name] = analyze_diagnostic_tool(path)
    
    elif args.tool_path:
        path = args.tool_path
        
        # Check if it's a shortcut
        if path.endswith('.lnk'):
            print(f"Resolving shortcut: {path}")
            target = find_shortcut_target(path)
            if target:
                path = target
                print(f"Target: {path}")
        
        results["tool"] = analyze_diagnostic_tool(path)
    
    else:
        # Interactive mode
        print("No tool specified. Scanning for all known tools...\n")
        found = analyze_all_tools()
        
        if found:
            print(f"\nFound {len(found)} tool(s). Analyzing...\n")
            for name, path in found:
                print(f"\n{'='*70}")
                print(f"Analyzing: {name}")
                print('='*70)
                results[name] = analyze_diagnostic_tool(path)
    
    # Save results
    output_file = Path("diagnostic_tools_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print()
    print("=" * 70)
    print(f"Analysis complete! Results saved to: {output_file.absolute()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
