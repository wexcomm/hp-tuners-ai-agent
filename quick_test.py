#!/usr/bin/env python3
"""
Quick J2534 Device Detection Test
Tests detection of TOPDON RLink X3 and other devices
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_topdon_detection():
    """Test TOPDON RLink X3 detection"""
    print("\n" + "="*60)
    print("TEST 1: TOPDON RLink X3 Detection")
    print("="*60)
    
    try:
        from skills.j2534_passthru.device_configs.topdon_rlink import TopdonRLinkX3Device
        
        device = TopdonRLinkX3Device()
        info = device.get_device_info()
        
        print(f"Device Name: {info['name']}")
        print(f"Manufacturer: {info['manufacturer']}")
        print(f"Install Path: {info.get('install_path', 'Not found')}")
        print(f"DLL Found: {'Yes' if info['dll_found'] else 'No'}")
        print(f"DLL Path: {info.get('dll_path', 'N/A')}")
        print(f"USB Connected: {'Yes' if info['connected'] else 'No'}")
        print(f"Protocols: {', '.join(info['protocols'])}")
        
        if info['dll_found']:
            print("\n[OK] TOPDON RLink X3 detected successfully!")
            return True
        else:
            print("\n[WARN] TOPDON DLL not found - is software installed?")
            return False
            
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def test_universal_detector():
    """Test universal J2534 device detection"""
    print("\n" + "="*60)
    print("TEST 2: Universal Device Detector")
    print("="*60)
    
    try:
        from skills.j2534_passthru.device_configs.generic.universal_detector import UniversalJ2534Detector
        
        detector = UniversalJ2534Detector()
        devices = detector.scan_system()
        
        print(f"Found {len(devices)} J2534 device(s):\n")
        
        for i, dev in enumerate(devices, 1):
            print(f"{i}. {dev.get('name', 'Unknown')}")
            print(f"   Vendor: {dev.get('vendor', 'Unknown')}")
            print(f"   Source: {dev.get('source', 'Unknown')}")
            if 'dll_path' in dev:
                print(f"   DLL: {dev['dll_path']}")
            print()
        
        best = detector.get_best_device()
        if best:
            print(f"[OK] Best device: {best.get('name', 'Unknown')}")
            return True
        else:
            print("[WARN] No devices found")
            return False
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_core_imports():
    """Test that core modules import correctly"""
    print("\n" + "="*60)
    print("TEST 3: Core Module Imports")
    print("="*60)
    
    tests = [
        ("J2534PassThru", "skills.j2534_passthru", "J2534PassThru"),
        ("FlashManager", "skills.j2534_passthru.flash", "FlashManager"),
        ("TOPDON Device", "skills.j2534_passthru.device_configs.topdon_rlink", "TopdonRLinkX3Device"),
        ("Universal Detector", "skills.j2534_passthru.device_configs.generic", "detect_any_device"),
    ]
    
    all_passed = True
    for name, module, obj in tests:
        try:
            exec(f"from {module} import {obj}")
            print(f"[OK] {name}")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            all_passed = False
    
    return all_passed


def test_dll_search():
    """Test DLL search in common locations"""
    print("\n" + "="*60)
    print("TEST 4: DLL Search Paths")
    print("="*60)
    
    search_paths = [
        r"C:\Program Files\TOPDON",
        r"C:\Program Files (x86)\TOPDON",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
    ]
    
    dll_patterns = ["*j2534*.dll", "*rlink*.dll", "*vci*.dll", "*passthru*.dll"]
    
    found_dlls = []
    
    for path_str in search_paths:
        path = Path(path_str)
        if not path.exists():
            continue
            
        print(f"\nSearching: {path}")
        for pattern in dll_patterns:
            try:
                for dll in path.rglob(pattern):
                    if dll.is_file():
                        print(f"  Found: {dll}")
                        found_dlls.append(dll)
            except PermissionError:
                print(f"  (Permission denied)")
    
    print(f"\n[OK] Found {len(found_dlls)} DLL(s)")
    return len(found_dlls) > 0


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  J2534 DEVICE DETECTION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("TOPDON Detection", test_topdon_detection()))
    results.append(("Universal Detector", test_universal_detector()))
    results.append(("Core Imports", test_core_imports()))
    results.append(("DLL Search", test_dll_search()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n[OK] All tests passed! Your J2534 setup is ready.")
    else:
        print("\n[WARN] Some tests failed. Check output above.")
    
    print("\n" + "="*60)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
