#!/usr/bin/env python3
"""
LFX Impala Specific Example
Demonstrates LFX 3.6L V6 specific monitoring and tuning
"""

import sys
sys.path.insert(0, '../src')

from hp_tuners_agent import HPTunersAgent
from lfx_impala_controller import LFXImpalaController

def main():
    print("LFX Impala Tuning Example")
    print("=" * 50)
    print("Vehicle: 2013 Chevrolet Impala 3.6L V6 (LFX)")
    print()
    
    # Get vehicle mileage
    mileage = int(input("Enter vehicle mileage: "))
    
    # Initialize agent
    agent = HPTunersAgent()
    
    print("\n1. Connecting to vehicle...")
    if not agent.initialize():
        print("❌ Failed to connect!")
        return
    
    print("✅ Connected")
    
    # Add LFX-specific controller
    lfx = LFXImpalaController(agent.ecu)
    
    # Check maintenance
    print("\n2. Pre-tune maintenance check...")
    maintenance = lfx.check_maintenance_items(mileage)
    for item in maintenance:
        print(f"   {item}")
    
    input("\nPress Enter to continue (or Ctrl+C to stop)...")
    
    # Get LFX-specific PIDs
    print("\n3. Configuring LFX-specific monitoring...")
    pids = lfx.get_lfx_logging_pids()
    print(f"   Monitoring {len(pids)} parameters")
    print("   Including: HPFP pressure, all 6 cylinder knock, VVT positions")
    
    # Log data
    print("\n4. Logging data...")
    print("   Drive for 10 minutes with varied conditions")
    import time
    time.sleep(3)
    
    log_data = agent.ecu.start_data_logging(pids, duration=600)
    print(f"   ✅ Collected {len(log_data)} samples")
    
    # LFX-specific analysis
    print("\n5. LFX-specific analysis...")
    
    # Fuel system (critical for DI)
    print("\n   📊 Fuel System Analysis:")
    fuel_analysis = lfx.analyze_lfx_fuel_system(log_data)
    print(f"      HPFP Health: {fuel_analysis['hpfp_health']}")
    print(f"      Injector Status: {fuel_analysis['injector_status']}")
    if fuel_analysis.get('warnings'):
        for warning in fuel_analysis['warnings']:
            print(f"      ⚠️  {warning}")
    
    # Knock analysis (all 6 cylinders)
    print("\n   📊 Knock Analysis:")
    knock_analysis = lfx.analyze_lfx_knock(log_data)
    print(f"      Total events: {knock_analysis['total_events']}")
    print(f"      Max knock: {knock_analysis['max_knock']}°")
    if knock_analysis['worst_cylinder']:
        print(f"      Worst cylinder: {knock_analysis['worst_cylinder']}")
    print(f"      Recommendation: {knock_analysis['fuel_recommendation']}")
    
    # VVT tracking
    print("\n   📊 VVT Analysis:")
    vvt_analysis = lfx.analyze_vvt_operation(log_data)
    print(f"      VVT Health: {vvt_analysis['vvt_health']}")
    print(f"      Intake Tracking: {vvt_analysis['intake_tracking']}")
    print(f"      Exhaust Tracking: {vvt_analysis['exhaust_tracking']}")
    
    # Generate tune
    print("\n6. Generating Stage 1 tune...")
    
    # Ask about octane
    print("\n   Fuel options:")
    print("   1. 87 octane (stock timing)")
    print("   2. 93 octane (timing advance)")
    choice = input("   Select (1/2): ")
    
    octane = 93 if choice == "2" else 87
    tune = lfx.generate_stage1_lfx_tune(octane_rating=octane)
    
    print(f"   ✅ Generated Stage 1 tune for {octane} octane")
    print(f"      Expected gain: {tune['metadata']['power_estimate']}")
    
    if octane == 87:
        print("\n   ⚠️  WARNING: 87 octane selected")
        print("      - No timing advance (12:1 compression knock-limited)")
        print("      - Use 93 octane for +8-10 HP gain")
    
    # Export
    print("\n7. Exporting tune...")
    output_file = f"lfx_stage1_{octane}oct.json"
    agent.ecu.export_to_hp_tuners_format(f"../{output_file}")
    print(f"   ✅ Exported: {output_file}")
    print(f"   Open in HP Tuners Editor, verify, then flash with MPVI2")
    
    # Pre-tune checklist
    print("\n8. Pre-tune checklist:")
    checklist = lfx.pre_tune_checklist()
    for category, items in checklist.items():
        print(f"\n   {category.replace('_', ' ').title()}:")
        for item in items:
            print(f"      ☐ {item}")
    
    # Shutdown
    print("\n9. Disconnecting...")
    agent.shutdown()
    print("✅ Complete!")
    
    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("1. Review the exported .json file")
    print("2. Open in HP Tuners Editor")
    print("3. Verify all tables match your modifications")
    print("4. Ensure stock tune backup exists")
    print("5. Flash with MPVI2")
    print("6. Log and verify results")
    print("7. Monitor HPFP pressure and knock closely")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()