#!/usr/bin/env python3
"""
Quick Start: Live Tuning Bridge Examples

This script demonstrates how to use the Live Tuning Bridge
for real-time sync with VCM Suite.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from live_tuning_bridge import LiveTuningBridge, BridgeConfig


def example_1_quick_generate():
    """Example 1: Quickly generate a tune without running the bridge"""
    print("="*60)
    print("Example 1: Quick Tune Generation")
    print("="*60)
    
    bridge = LiveTuningBridge()
    
    # Generate a Stage 1 tune
    output_dir = bridge.quick_generate(
        vin="2G1WB5E37D1157819",
        octane=93,
        mods=["intake", "exhaust"]
    )
    
    print(f"\nTune generated at: {output_dir}")
    print("\nNext steps:")
    print("1. Open VCM Editor")
    print("2. File > Open your stock tune")
    print("3. Navigate to tables (Engine > Spark, Engine > Fuel, etc.)")
    print("4. Copy values from CSV files in the output folder")
    print("5. Paste into VCM Editor tables")
    print("6. File > Save As: Stage1_Intake_Exhaust_93oct.hpt")
    

def example_2_request_file():
    """Example 2: Create a tune request file for the bridge to process"""
    print("\n" + "="*60)
    print("Example 2: Create Tune Request File")
    print("="*60)
    
    bridge = LiveTuningBridge()
    
    # Create a request file - the bridge will auto-process it
    request_file = bridge.create_tune_request(
        vin="2G1WB5E37D1157819",
        octane=91,  # 91 octane
        mods=["intake", "exhaust", "headers"],
        tune_type="stage1"
    )
    
    print(f"\nRequest created: {request_file}")
    print("\nTo auto-process:")
    print("1. Start the bridge: python src/live_tuning_bridge.py")
    print("2. The tune will be generated automatically")
    print("3. Find outputs in: ./bridge/outgoing/")


def example_3_analyze_log():
    """Example 3: Analyze a VCM Scanner log"""
    print("\n" + "="*60)
    print("Example 3: Analyze VCM Scanner Log")
    print("="*60)
    
    bridge = LiveTuningBridge()
    
    print("\nTo analyze a log with the bridge running:")
    print("1. Export CSV from VCM Scanner")
    print("2. Copy/move the file to: ./bridge/incoming/")
    print("3. Bridge will auto-analyze and alert you to issues")
    print("4. Analysis saved to: ./bridge/incoming/analysis_*.json")
    
    # Or analyze directly
    # from enhanced_agent import analyze_log_file
    # results = analyze_log_file("path/to/your/log.csv")
    # print(results)


def example_4_custom_config():
    """Example 4: Custom bridge configuration"""
    print("\n" + "="*60)
    print("Example 4: Custom Configuration")
    print("="*60)
    
    # Custom config with different directories
    config = BridgeConfig(
        bridge_dir="C:/Tuning/Bridge",
        outgoing_dir="C:/Tuning/ToVCM",
        incoming_dir="C:/Tuning/FromVCM",
        knock_threshold=3.0,  # More sensitive knock detection
        fuel_trim_threshold=3.0,  # More sensitive fuel trim alerts
    )
    
    bridge = LiveTuningBridge(config)
    
    print(f"\nCustom bridge configured:")
    print(f"  Outgoing: {config.outgoing_dir}")
    print(f"  Incoming: {config.incoming_dir}")
    print(f"  Knock threshold: {config.knock_threshold}°")
    print(f"  Fuel trim threshold: ±{config.fuel_trim_threshold}%")
    

def example_5_run_bridge():
    """Example 5: Run the bridge interactively"""
    print("\n" + "="*60)
    print("Example 5: Run Live Bridge")
    print("="*60)
    
    print("\nTo start the bridge:")
    print("  python src/live_tuning_bridge.py")
    print("\nOr from this script:")
    print("  bridge = LiveTuningBridge()")
    print("  bridge.start()  # Press Ctrl+C to stop")
    
    print("\nWhile running, the bridge will:")
    print("  • Watch ./bridge/outgoing/ for tune requests")
    print("  • Watch ./bridge/incoming/ for VCM Scanner logs")
    print("  • Auto-generate tunes in VCM-compatible formats")
    print("  • Auto-analyze logs and alert on issues")
    print("  • Archive processed files")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("  LIVE TUNING BRIDGE - QUICK START EXAMPLES")
    print("="*60)
    
    examples = [
        ("Quick Generate", example_1_quick_generate),
        ("Request File", example_2_request_file),
        ("Analyze Log", example_3_analyze_log),
        ("Custom Config", example_4_custom_config),
        ("Run Bridge", example_5_run_bridge),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n[{i}/{len(examples)}] {name}")
        print("-" * 40)
        func()
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("  EXAMPLES COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run the bridge: python src/live_tuning_bridge.py")
    print("3. Or quick generate: python src/live_tuning_bridge.py --quick YOURVIN")


if __name__ == "__main__":
    main()
