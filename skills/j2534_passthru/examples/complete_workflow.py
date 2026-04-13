#!/usr/bin/env python3
"""
Complete Tuning Workflow with J2534 PassThru

This example shows the complete workflow from reading stock flash
to modifying and flashing back using J2534 PassThru device.
"""

import sys
from pathlib import Path

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'hpt_converter'))

from core import J2534PassThru
from flash import FlashManager
from diagnostics import DiagnosticsManager
from builder import HPTBuilder
from checksum import ChecksumValidator


def workflow_1_read_stock_flash():
    """
    Step 1: Read stock flash from vehicle for backup
    """
    print("=" * 70)
    print("WORKFLOW 1: Read Stock Flash")
    print("=" * 70)
    
    pt = J2534PassThru()
    
    try:
        print("1. Opening J2534 device...")
        pt.open()
        
        print("2. Connecting to vehicle...")
        channel = pt.connect_can(baud_rate=500000)
        
        # Get ECU info first
        diag = DiagnosticsManager(pt)
        info = diag.get_ecu_info()
        
        print(f"   VIN: {info['vin']}")
        print(f"   Calibration: {info['calibration_id']}")
        print(f"   Battery: {info['battery_voltage']:.1f}V")
        
        # Read flash
        print("\n3. Reading flash memory (this may take 5-10 minutes)...")
        
        flash = FlashManager(pt)
        flash.set_platform("GM_E37")
        
        def progress(current, total):
            pct = (current / total) * 100
            print(f"\r   Progress: {pct:.1f}% ({current}/{total} bytes)", 
                  end='', flush=True)
        
        flash.backup_flash("stock_backup.bin", progress_callback=progress)
        print("\n\n✓ Stock flash saved: stock_backup.bin")
        
        pt.disconnect(channel)
        pt.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
        
    return True


def workflow_2_modify_tune():
    """
    Step 2: Modify the stock tune using HPTBuilder
    """
    print("\n" + "=" * 70)
    print("WORKFLOW 2: Modify Tune")
    print("=" * 70)
    
    try:
        print("1. Loading stock flash...")
        
        builder = HPTBuilder(
            platform="GM_E37",
            vin="2G1WB5E37D1157819",
            calibration_id="12653917"
        )
        builder.load_base_binary("stock_backup.bin")
        
        print("2. Applying modifications...")
        
        # Example modifications
        builder.set_rev_limit(7000)
        builder.set_speed_limit(160)
        
        # Add comment
        builder.add_comment("Stage 1 Tune - Intake and Exhaust")
        
        print("3. Validating checksums...")
        
        # Save with automatic checksum fixing
        builder.save("stage1_tune.bin", fix_checksums=True)
        
        print("\n✓ Modified tune saved: stage1_tune.bin")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
        
    return True


def workflow_3_validate_before_flash():
    """
    Step 3: Validate checksums before flashing
    """
    print("\n" + "=" * 70)
    print("WORKFLOW 3: Validate Before Flash")
    print("=" * 70)
    
    try:
        print("1. Validating modified tune...")
        
        validator = ChecksumValidator(platform="GM_E37")
        report = validator.validate_binary("stage1_tune.bin")
        
        validator.print_report(report)
        
        if not report.overall_valid:
            print("\n✗ Checksums invalid! Cannot flash.")
            return False
        
        print("\n✓ Checksums valid - safe to flash")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
        
    return True


def workflow_4_flash_to_ecu():
    """
    Step 4: Flash the modified tune to ECU
    """
    print("\n" + "=" * 70)
    print("WORKFLOW 4: Flash to ECU")
    print("=" * 70)
    
    print("⚠️  WARNING: This will modify your ECU!")
    input("\nPress Enter to continue or Ctrl+C to abort...")
    
    pt = J2534PassThru()
    
    try:
        print("\n1. Opening J2534 device...")
        pt.open()
        
        print("2. Checking battery voltage...")
        voltage = pt.get_battery_voltage()
        print(f"   Battery: {voltage:.1f}V")
        
        if voltage < 12.0:
            print("✗ Battery voltage too low!")
            return False
        
        print("3. Connecting to vehicle...")
        channel = pt.connect_can()
        
        print("4. Flashing modified tune...")
        
        flash = FlashManager(pt)
        flash.set_platform("GM_E37")
        
        def progress(current, total):
            pct = (current / total) * 100
            print(f"\r   Progress: {pct:.1f}% ({current}/{total} bytes)", 
                  end='', flush=True)
        
        flash.flash_binary("stage1_tune.bin", verify=True, 
                          progress_callback=progress)
        
        print("\n\n✓ Flash complete!")
        
        pt.disconnect(channel)
        pt.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
        
    return True


def main():
    """Run workflow examples"""
    print("\nJ2534 + HPT Converter Complete Workflow")
    print("=" * 70)
    print("""
This demonstrates complete tuning workflow:
1. Read stock flash from ECU
2. Modify tune using HPTBuilder
3. Validate checksums
4. Flash to ECU
""")
    
    print("\nNote: This is example code. Update paths and VIN before running.")


if __name__ == "__main__":
    main()
