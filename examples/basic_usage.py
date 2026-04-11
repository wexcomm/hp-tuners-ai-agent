#!/usr/bin/env python3
"""
Basic Usage Example for HP Tuners AI Agent
Demonstrates connecting to vehicle and logging data
"""

import sys
sys.path.insert(0, '../src')

from hp_tuners_agent import HPTunersAgent

def main():
    print("HP Tuners AI Agent - Basic Usage Example")
    print("=" * 50)
    
    # Initialize agent
    agent = HPTunersAgent()
    
    print("\n1. Connecting to vehicle...")
    # Use auto-detect or specify port: port="/dev/rfcomm0" for Bluetooth
    if not agent.initialize():
        print("❌ Failed to connect!")
        print("   Ensure OBD-II adapter is connected/paired")
        return
    
    print("✅ Connected to vehicle")
    
    # Read ECU info
    print("\n2. Reading ECU information...")
    info = agent.ecu.read_ecu_info()
    print(f"   VIN: {info.vin}")
    print(f"   Calibration: {info.calibration_id}")
    
    # Backup stock tune
    print("\n3. Creating stock tune backup...")
    backup_file = agent.backup_stock_tune()
    print(f"   Backup saved: {backup_file}")
    
    # Log baseline data
    print("\n4. Logging baseline data...")
    print("   Instructions: Drive normally for 10 minutes")
    print("   Include: idle, cruise, and WOT acceleration")
    print("   Starting in 5 seconds...")
    import time
    time.sleep(5)
    
    log_file = agent.log_baseline(duration=600)  # 10 minutes
    print(f"   ✅ Log saved: {log_file}")
    
    # Analyze data
    print("\n5. Analyzing data...")
    if agent.ecu.data_log:
        knock_analysis = agent.ecu.analyze_knock(agent.ecu.data_log)
        fuel_analysis = agent.ecu.analyze_fuel_trims(agent.ecu.data_log)
        
        print(f"   Knock events: {knock_analysis['total_events']}")
        print(f"   Fuel trim recommendation: {fuel_analysis['recommendation']}")
    
    # Shutdown
    print("\n6. Disconnecting...")
    agent.shutdown()
    print("✅ Done!")

if __name__ == "__main__":
    main()