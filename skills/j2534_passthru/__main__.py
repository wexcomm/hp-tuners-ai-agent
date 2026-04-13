#!/usr/bin/env python3
"""
J2534 PassThru CLI
Command-line interface for J2534 operations
"""

import sys
import argparse
import time
from pathlib import Path

try:
    from .core import J2534PassThru, Protocol, J2534Error
    from .flash import FlashManager
    from .diagnostics import DiagnosticsManager
except ImportError:
    from core import J2534PassThru, Protocol, J2534Error
    from flash import FlashManager
    from diagnostics import DiagnosticsManager


def cmd_info(args):
    """Get ECU information"""
    print("Connecting to J2534 device...")
    
    try:
        pt = J2534PassThru()
        pt.open()
        channel = pt.connect_can()
        
        diag = DiagnosticsManager(pt)
        info = diag.get_ecu_info()
        
        print("\nECU Information:")
        print("=" * 50)
        print(f"VIN:              {info['vin']}")
        print(f"Calibration ID:   {info['calibration_id']}")
        print(f"Protocol:         {info['protocol']}")
        print(f"Battery Voltage:  {info['battery_voltage']:.1f}V")
        
        pt.disconnect(channel)
        pt.close()
        
    except J2534Error as e:
        print(f"Error: {e}")
        return 1
        
    return 0


def cmd_test(args):
    """Test connection to device and vehicle"""
    print("Testing J2534 connection...")
    
    try:
        pt = J2534PassThru()
        pt.open()
        print("✓ Device opened successfully")
        
        voltage = pt.get_battery_voltage()
        print(f"✓ Battery voltage: {voltage:.1f}V")
        
        if voltage < 12.0:
            print("⚠ Warning: Battery voltage low")
            
        channel = pt.connect_can()
        print("✓ Connected to vehicle CAN bus")
        
        vin = pt.read_vin()
        print(f"✓ VIN: {vin}")
        
        pt.disconnect(channel)
        pt.close()
        print("\nAll tests passed!")
        
    except J2534Error as e:
        print(f"✗ Error: {e}")
        return 1
        
    return 0


def cmd_flash(args):
    """Flash binary to ECU"""
    print(f"Flashing: {args.input}")
    print(f"Platform: {args.platform}")
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1
        
    try:
        pt = J2534PassThru()
        pt.open()
        channel = pt.connect_can()
        
        flash = FlashManager(pt)
        flash.set_platform(args.platform)
        
        # Progress callback
        def progress(current, total):
            pct = (current / total) * 100
            print(f"\rProgress: {pct:.1f}% ({current}/{total} bytes)", end='', flush=True)
            
        # Flash
        flash.flash_binary(args.input, verify=args.verify, 
                          progress_callback=progress)
        print("\n✓ Flash complete!")
        
        pt.disconnect(channel)
        pt.close()
        
    except J2534Error as e:
        print(f"\n✗ Flash failed: {e}")
        return 1
        
    return 0


def cmd_read_flash(args):
    """Read ECU flash to file"""
    print(f"Reading flash to: {args.output}")
    print(f"Platform: {args.platform}")
    
    # Determine size
    sizes = {
        'GM_E37': 1024 * 1024,
        'GM_E38': 1024 * 1024,
        'GM_E41': 2 * 1024 * 1024,
    }
    
    size = args.size
    if size is None:
        size = sizes.get(args.platform, 1024 * 1024)
    elif size.endswith('MB') or size.endswith('mb'):
        size = int(size[:-2]) * 1024 * 1024
    elif size.endswith('KB') or size.endswith('kb'):
        size = int(size[:-2]) * 1024
    else:
        size = int(size)
        
    try:
        pt = J2534PassThru()
        pt.open()
        channel = pt.connect_can()
        
        flash = FlashManager(pt)
        flash.set_platform(args.platform)
        
        # Progress callback
        def progress(current, total):
            pct = (current / total) * 100
            print(f"\rProgress: {pct:.1f}% ({current}/{total} bytes)", end='', flush=True)
            
        # Read flash
        flash.backup_flash(args.output, progress_callback=progress)
        print("\n✓ Flash read complete!")
        
        pt.disconnect(channel)
        pt.close()
        
    except J2534Error as e:
        print(f"\n✗ Read failed: {e}")
        return 1
        
    return 0


def cmd_dtc(args):
    """Read/clear DTCs"""
    try:
        pt = J2534PassThru()
        pt.open()
        channel = pt.connect_can()
        
        diag = DiagnosticsManager(pt)
        
        if args.clear:
            print("Clearing DTCs...")
            diag.clear_dtcs(channel)
            print("✓ DTCs cleared")
        else:
            print("Reading DTCs...")
            dtcs = diag.read_dtcs(channel)
            
            if dtcs:
                print(f"\nFound {len(dtcs)} DTCs:")
                for dtc in dtcs:
                    print(f"  {dtc['code']}: {dtc.get('description', 'Unknown')}")
            else:
                print("No DTCs found")
                
        pt.disconnect(channel)
        pt.close()
        
    except J2534Error as e:
        print(f"Error: {e}")
        return 1
        
    return 0


def cmd_log(args):
    """Log live data"""
    print(f"Logging for {args.duration} seconds...")
    print("Press Ctrl+C to stop")
    
    try:
        pt = J2534PassThru()
        pt.open()
        channel = pt.connect_can()
        
        diag = DiagnosticsManager(pt)
        
        # Default PIDs if none specified
        pids = args.pids or [0x0C, 0x0D, 0x05, 0x0A]  # RPM, Speed, Coolant, MAP
        
        def print_data(timestamp, data):
            values = []
            for pid, val in data.items():
                values.append(f"{pid:02X}:{val['value']:.1f}{val.get('unit', '')}")
            print(f"\r[{timestamp:6.2f}s] {' | '.join(values)}", end='', flush=True)
            
        try:
            logs = diag.start_data_log(
                pids=pids,
                duration=args.duration,
                interval=args.interval,
                callback=print_data,
                channel_id=channel
            )
        except KeyboardInterrupt:
            print("\n\nStopped by user")
            
        # Save to file if requested
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(logs, f, indent=2)
            print(f"\nLog saved: {args.output}")
            
        pt.disconnect(channel)
        pt.close()
        
    except J2534Error as e:
        print(f"Error: {e}")
        return 1
        
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='J2534 PassThru - Direct ECU communication'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # info command
    p_info = subparsers.add_parser('info', help='Get ECU information')
    
    # test command
    p_test = subparsers.add_parser('test', help='Test connection')
    
    # flash command
    p_flash = subparsers.add_parser('flash', help='Flash binary to ECU')
    p_flash.add_argument('input', help='Input binary file')
    p_flash.add_argument('--platform', '-p', default='GM_E37',
                        help='Platform (GM_E37, GM_E38, etc.)')
    p_flash.add_argument('--no-verify', action='store_true',
                        help='Skip verification after flash')
    
    # read_flash command
    p_read = subparsers.add_parser('read_flash', help='Read ECU flash')
    p_read.add_argument('output', help='Output file path')
    p_read.add_argument('--platform', '-p', default='GM_E37')
    p_read.add_argument('--size', '-s', help='Size to read (e.g., 1MB, 1024KB)')
    
    # dtc command
    p_dtc = subparsers.add_parser('dtc', help='Read/clear DTCs')
    p_dtc.add_argument('--clear', '-c', action='store_true',
                      help='Clear DTCs instead of reading')
    
    # log command
    p_log = subparsers.add_parser('log', help='Log live data')
    p_log.add_argument('--duration', '-d', type=float, default=60.0,
                      help='Logging duration in seconds')
    p_log.add_argument('--interval', '-i', type=float, default=0.1,
                      help='Sample interval in seconds')
    p_log.add_argument('--pids', type=lambda s: [int(x, 16) for x in s.split(',')],
                      help='Comma-separated list of PIDs (hex)')
    p_log.add_argument('--output', '-o', help='Output JSON file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    # Execute command
    commands = {
        'info': cmd_info,
        'test': cmd_test,
        'flash': cmd_flash,
        'read_flash': cmd_read_flash,
        'dtc': cmd_dtc,
        'log': cmd_log,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
