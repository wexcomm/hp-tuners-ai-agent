#!/usr/bin/env python3
"""
Complete Stage 1 Tuning Workflow Example
Demonstrates the full HP Tuners AI + VCM Suite workflow
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_agent import EnhancedHPTunersAgent, quick_stage1_tune, analyze_log_file
from pathlib import Path

def main():
    print("=" * 70)
    print("HP Tuners AI Agent - Stage 1 Tuning Workflow Example")
    print("=" * 70)
    
    # Initialize agent
    print("\n1. Initializing AI Agent...")
    agent = EnhancedHPTunersAgent(
        port="COM3",  # Change to your MPVI2 port
        backups_dir="./tune_backups"
    )
    
    # ========================================================================
    # PHASE 1: PRE-TUNE DIAGNOSTIC
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Pre-Tune Diagnostic")
    print("=" * 70)
    
    print("\n2. Connecting to vehicle...")
    if not agent.initialize():
        print("Failed to connect. Ensure MPVI2 is connected.")
        return
    
    print("Connected to vehicle")
    
    # Read ECU info
    info = agent.ecu.read_ecu_info()
    print(f"\n   VIN: {info.vin}")
    print(f"   Calibration: {info.calibration_id}")
    
    # Pre-tune diagnostic
    print("\n3. Running pre-tune diagnostic...")
    result = agent.pre_tune_diagnostic()
    
    print(f"\n   DTCs Present: {len(result['diagnostic_report']['codes'])}")
    print(f"   Safe to Tune: {'YES' if result['safe_to_tune'] else 'NO'}")
    
    if result['warnings']:
        print("\n   Warnings:")
        for warning in result['warnings']:
            print(f"      ! {warning}")
    
    if not result['safe_to_tune']:
        print("\nABORT: Fix issues before proceeding with tune!")
        return
    
    # Backup stock tune
    print("\n4. Backing up stock tune...")
    backup_path = agent.backup_stock_tune()
    print(f"   Stock tune saved: {backup_path}")
    
    # ========================================================================
    # PHASE 2: BASELINE DATA LOGGING
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Baseline Data Logging")
    print("=" * 70)
    
    print("\n5. Starting baseline logging...")
    print("   Instructions:")
    print("      - 5 min idle")
    print("      - Normal driving 0-50 mph")
    print("      - 3x WOT pulls from 2500-6500 RPM")
    print("      - Highway cruise")
    
    log_path = agent.log_with_preset(
        preset="lfx_full",
        duration=600,  # 10 minutes
        output="./logs/baseline.csv"
    )
    print(f"\n   Log saved: {log_path}")
    
    # ========================================================================
    # PHASE 3: AI ANALYSIS
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: AI Analysis")
    print("=" * 70)
    
    print("\n6. Analyzing baseline log...")
    results = agent.import_vcm_scanner_log(log_path)
    
    summary = results['summary']
    print(f"\n   Analysis Results:")
    print(f"      WOT Events: {summary['wot_events']}")
    print(f"      RPM Range: {summary['rpm_range']['min']:.0f} - {summary['rpm_range']['max']:.0f}")
    print(f"      Knock Events: {summary['knock_analysis']['total_events']}")
    print(f"      Max Knock Retard: {summary['knock_analysis']['max_retard']:.1f} deg")
    
    fuel = summary['fuel_analysis']
    print(f"      Fuel Trims: STFT avg = {fuel.get('stft_avg', 0):.1f}%")
    
    # AI Recommendations
    print("\n7. AI Recommendations:")
    for rec in results['recommendations']:
        print(f"\n   [{rec['priority']}] {rec['category']}")
        print(f"      Issue: {rec['issue']}")
        print(f"      Action: {rec['action']}")
    
    # ========================================================================
    # PHASE 4: GENERATE STAGE 1 TUNE
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Generate Stage 1 Tune")
    print("=" * 70)
    
    print("\n8. Creating Stage 1 tune package...")
    
    # Determine octane based on analysis
    recommended_octane = 93 if summary['knock_analysis']['max_retard'] < 2 else 91
    
    hpt = agent.create_stage1_tune_package(
        octane=recommended_octane,
        mods=["intake", "exhaust"]
    )
    
    print(f"\n   Tune created with {len(hpt.tables)} tables")
    print(f"   Octane: {recommended_octane}")
    
    # Export
    print("\n9. Exporting tune files...")
    exported = agent.export_tune("./tunes/stage1", format="all")
    
    print(f"\n   Exported Files:")
    for key, path in exported.items():
        print(f"      {key}: {path}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS (Manual in VCM Editor):")
    print("=" * 70)
    print("""
   1. Open VCM Editor
   2. Load your stock tune file
   3. Import CSV tables from:
      ./tunes/stage1/csv_tables_*/
   4. Review each table before flashing
   5. Flash using Vehicle -> Write -> Write Calibration
   6. Return to this script for verification
    """)
    
    # ========================================================================
    # PHASE 5: VERIFICATION (After flashing in VCM Editor)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Verification (After Flashing)")
    print("=" * 70)
    
    input("\n   Press ENTER after you've flashed the tune in VCM Editor...")
    
    print("\n10. Clearing DTCs...")
    agent.clear_dtcs()
    print("   DTCs cleared")
    
    print("\n11. Running verification logging...")
    verify_path = agent.log_with_preset(
        preset="lfx_full",
        duration=600,
        output="./logs/stage1_verification.csv"
    )
    
    print("\n12. Analyzing verification log...")
    verify_results = agent.import_vcm_scanner_log(verify_path)
    
    v_summary = verify_results['summary']
    
    print(f"\n   Verification Results:")
    print(f"      WOT Events: {v_summary['wot_events']}")
    print(f"      Max Knock: {v_summary['knock_analysis']['max_retard']:.1f} deg")
    print(f"      Fuel Trims: {v_summary['fuel_analysis'].get('stft_avg', 0):.1f}%")
    
    # Check for new DTCs
    codes = agent.read_dtcs()
    if codes:
        print(f"\n   Warning: New DTCs after flash:")
        for code in codes:
            print(f"      {code['code']}: {code['description']}")
    else:
        print("\n   No new DTCs detected")
    
    # Final assessment
    print("\n" + "=" * 70)
    print("FINAL ASSESSMENT")
    print("=" * 70)
    
    issues = []
    
    if v_summary['knock_analysis']['max_retard'] > 4:
        issues.append("Excessive knock detected - reduce timing 2-4 deg")
    
    if v_summary['fuel_analysis'].get('correction_needed'):
        issues.append("Fuel trims off - adjust MAF calibration")
    
    if codes:
        issues.append("New DTCs present after flash")
    
    if not issues:
        print("\n   TUNE VERIFIED SUCCESSFULLY!")
        print("\n   Your Stage 1 tune is working correctly.")
        print("   Continue monitoring logs on subsequent drives.")
    else:
        print("\n   ISSUES DETECTED:")
        for issue in issues:
            print(f"      - {issue}")
        print("\n   Recommend revising tune based on AI suggestions above.")
    
    # Generate final report
    print("\n13. Generating final report...")
    report_path = "./tunes/final_report.json"
    agent.generate_full_report(report_path)
    print(f"   Report saved: {report_path}")
    
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    
    agent.shutdown()


if __name__ == "__main__":
    # Quick mode without vehicle connection
    if "--quick" in sys.argv:
        print("Quick Mode: Generating Stage 1 tune without vehicle connection\n")
        
        tune_path = quick_stage1_tune(
            vin="2G1WB5E37D1157819",
            octane=93,
            output_dir="./tunes"
        )
        
        print(f"\nTune exported to: {tune_path}")
        print("\nImport CSV tables from this directory into VCM Editor")
        
    # Analysis only mode
    elif "--analyze" in sys.argv and len(sys.argv) > 2:
        log_file = sys.argv[2]
        print(f"Analysis Mode: Analyzing {log_file}\n")
        
        results = analyze_log_file(log_file)
        
        print(f"WOT Events: {results['summary']['wot_events']}")
        print(f"Knock Max: {results['summary']['knock_analysis']['max_retard']} deg")
        
        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"\n[{rec['priority']}] {rec['category']}")
            print(f"  {rec['action']}")
            
    else:
        main()
