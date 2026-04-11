#!/usr/bin/env python3
"""
LFX 3.6L V6 (2013 Impala) Specific Controller
Extends the HP Tuners Master Agent with LFX-specific tuning capabilities
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LFXSpecificPIDs:
    """LFX-specific OBD-II PIDs that differ from standard"""
    HPFP_PRESSURE: str = "0152"  # High Pressure Fuel Pump (MPa)
    LPFP_PRESSURE: str = "0153"  # Low Pressure Fuel Pump (psi)
    VVT_INTAKE_CMD: str = "1161"  # Commanded intake position
    VVT_INTAKE_ACT: str = "1162"  # Actual intake position
    VVT_EXHAUST_CMD: str = "1163"  # Commanded exhaust position
    VVT_EXHAUST_ACT: str = "1164"  # Actual exhaust position
    INJECTOR_DUTY: str = "1170"  # Injector duty cycle
    CYLINDER_HEAD_TEMP: str = "1158"  # Cylinder head temperature
    FUEL_TRIM_CELL: str = "1159"  # Current fuel trim cell
    KNOCK_RETARD_CYL1: str = "11A0"
    KNOCK_RETARD_CYL2: str = "11A1"
    KNOCK_RETARD_CYL3: str = "11A2"
    KNOCK_RETARD_CYL4: str = "11A3"
    KNOCK_RETARD_CYL5: str = "11A4"
    KNOCK_RETARD_CYL6: str = "11A5"


class LFXImpalaController:
    """LFX 3.6L V6 specific tuning controller for 2013 Chevrolet Impala"""
    
    def __init__(self, ecu_controller):
        self.ecu = ecu_controller
        self.profile = self._load_profile()
        self.lfx_pids = LFXSpecificPIDs()
        self.critical_warnings = []
        
    def _load_profile(self) -> Dict:
        """Load LFX Impala profile"""
        # Load from profile file or use default
        default_profile = {
            "engine": {
                "code": "LFX",
                "displacement": 3.6,
                "compression_ratio": 12.0,
                "redline_rpm": 7000,
                "fuel_cut_rpm": 7200,
                "max_hp": 305,
                "max_torque_nm": 358
            },
            "fuel_system": {
                "hpfp_idle_mpa": 5.0,
                "hpfp_wot_mpa": 12.0,
                "hpfp_max_mpa": 15.0,
                "injector_max_duty": 85,
                "fuel_pressure_critical": 4.0
            },
            "transmission": {
                "type": "6T70",
                "max_torque_lbft": 350,
                "stock_line_pressure": 85,
                "performance_line_pressure": 95,
                "max_safe_line_pressure": 110
            }
        }
        return default_profile
    
    def get_lfx_logging_pids(self) -> List[str]:
        """Return list of PIDs essential for LFX tuning"""
        # Standard PIDs
        standard = [
            "RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS",
            "MAF", "O2_B1S1", "O2_B2S1",
            "SHORT_FUEL_TRIM", "LONG_FUEL_TRIM",
            "SPARK_ADV", "COOLANT_TEMP", "INTAKE_TEMP"
        ]
        
        # LFX-specific PIDs (these require Mode 22 on GM vehicles)
        lfx_specific = [
            "HPFP_PRESSURE",  # Critical for DI engine
            "INJECTOR_DUTY",  # Watch for fuel system limits
            "CYLINDER_HEAD_TEMP",  # High compression runs hot
            "KNOCK_RETARD_CYL1",  # Monitor all cylinders
            "KNOCK_RETARD_CYL2",
            "KNOCK_RETARD_CYL3",
            "KNOCK_RETARD_CYL4",
            "KNOCK_RETARD_CYL5",
            "KNOCK_RETARD_CYL6",
            "VVT_INTAKE_ACT",  # Verify VVT operation
            "VVT_EXHAUST_ACT",
            "FUEL_TRIM_CELL"  # GM-specific cell tracking
        ]
        
        return standard + lfx_specific
    
    def analyze_lfx_fuel_system(self, log_data: List[Dict]) -> Dict:
        """Analyze LFX direct injection fuel system health"""
        
        hpfp_readings = []
        injector_duty_readings = []
        
        for entry in log_data:
            hpfp = entry.get('HPFP_PRESSURE')
            if hpfp is not None:
                hpfp_readings.append(hpfp)
            
            duty = entry.get('INJECTOR_DUTY')
            if duty is not None:
                injector_duty_readings.append(duty)
        
        analysis = {
            "hpfp_health": "Unknown",
            "injector_status": "Unknown",
            "can_increase_power": True,
            "warnings": [],
            "recommendations": []
        }
        
        if hpfp_readings:
            min_hpfp = min(hpfp_readings)
            avg_hpfp = sum(hpfp_readings) / len(hpfp_readings)
            
            # Check HPFP pressure
            if min_hpfp < 4.0:
                analysis["hpfp_health"] = "CRITICAL"
                analysis["warnings"].append(f"HPFP pressure dropped to {min_hpfp:.1f} MPa - fuel starvation risk!")
                analysis["can_increase_power"] = False
                analysis["recommendations"].append("DO NOT INCREASE FUEL DEMAND - HPFP failing or undersized")
            elif min_hpfp < 10.0:
                analysis["hpfp_health"] = "Warning"
                analysis["warnings"].append(f"HPFP pressure low: {min_hpfp:.1f} MPa at high load")
                analysis["recommendations"].append("Check low pressure fuel pump (in tank) first")
            else:
                analysis["hpfp_health"] = "Good"
        
        if injector_duty_readings:
            max_duty = max(injector_duty_readings)
            avg_duty = sum(injector_duty_readings) / len(injector_duty_readings)
            
            analysis["injector_duty_max"] = max_duty
            analysis["injector_duty_avg"] = avg_duty
            
            if max_duty > 90:
                analysis["injector_status"] = "CRITICAL"
                analysis["warnings"].append(f"Injector duty cycle maxed at {max_duty:.1f}% - at fuel system limit!")
                analysis["can_increase_power"] = False
                analysis["recommendations"].append("UPGRADE INJECTORS before any power increase")
            elif max_duty > 85:
                analysis["injector_status"] = "Near Limit"
                analysis["warnings"].append(f"Injector duty high: {max_duty:.1f}% - limited headroom")
                analysis["recommendations"].append("Monitor closely with any fuel increases")
            else:
                analysis["injector_status"] = "Good"
                analysis["recommendations"].append(f"Injector duty max {max_duty:.1f}%, headroom available")
        
        return analysis
    
    def analyze_lfx_knock(self, log_data: List[Dict]) -> Dict:
        """Analyze knock on all 6 cylinders - critical for 12:1 compression"""
        
        cylinders = ["CYL1", "CYL2", "CYL3", "CYL4", "CYL5", "CYL6"]
        knock_data = {cyl: [] for cyl in cylinders}
        
        for entry in log_data:
            for i, cyl in enumerate(cylinders, 1):
                pid_name = f"KNOCK_RETARD_CYL{i}"
                value = entry.get(pid_name)
                if value is not None and value > 0:
                    knock_data[cyl].append({
                        "value": value,
                        "rpm": entry.get("RPM"),
                        "load": entry.get("ENGINE_LOAD")
                    })
        
        analysis = {
            "cylinder_analysis": {},
            "total_events": 0,
            "max_knock": 0,
            "worst_cylinder": None,
            "fuel_recommendation": "87 octane acceptable",
            "timing_safe": True,
            "warnings": []
        }
        
        for cyl in cylinders:
            events = knock_data[cyl]
            if events:
                max_knock = max(e["value"] for e in events)
                analysis["cylinder_analysis"][cyl] = {
                    "event_count": len(events),
                    "max_knock": max_knock,
                    "events": events[:5]  # First 5 events
                }
                analysis["total_events"] += len(events)
                
                if max_knock > analysis["max_knock"]:
                    analysis["max_knock"] = max_knock
                    analysis["worst_cylinder"] = cyl
        
        # Recommendations based on knock levels
        if analysis["max_knock"] == 0:
            analysis["fuel_recommendation"] = "Running clean on current fuel. Can try 93 octane for +3-4° timing"
        elif analysis["max_knock"] < 2:
            analysis["fuel_recommendation"] = "Minor knock on current fuel. Use 93 octane for timing advance"
        elif analysis["max_knock"] < 4:
            analysis["fuel_recommendation"] = "Moderate knock detected. Must use 93 octane. Consider retarding timing 2°"
            analysis["timing_safe"] = False
        else:
            analysis["fuel_recommendation"] = "SEVERE KNOCK! Immediately retard timing 4-6° or switch to 93+ octane"
            analysis["timing_safe"] = False
            analysis["warnings"].append(f"Critical knock detected: {analysis['max_knock']:.1f}° on {analysis['worst_cylinder']}")
        
        return analysis
    
    def analyze_vvt_operation(self, log_data: List[Dict]) -> Dict:
        """Analyze VVT tracking - important for LFX with dual VVT"""
        
        intake_deviations = []
        exhaust_deviations = []
        
        for entry in log_data:
            intake_cmd = entry.get('VVT_INTAKE_CMD')
            intake_act = entry.get('VVT_INTAKE_ACT')
            exhaust_cmd = entry.get('VVT_EXHAUST_CMD')
            exhaust_act = entry.get('VVT_EXHAUST_ACT')
            
            if intake_cmd is not None and intake_act is not None:
                deviation = abs(intake_cmd - intake_act)
                intake_deviations.append(deviation)
            
            if exhaust_cmd is not None and exhaust_act is not None:
                deviation = abs(exhaust_cmd - exhaust_act)
                exhaust_deviations.append(deviation)
        
        analysis = {
            "intake_tracking": "Unknown",
            "exhaust_tracking": "Unknown",
            "vvt_health": "Unknown",
            "warnings": [],
            "recommendations": []
        }
        
        if intake_deviations:
            max_intake_dev = max(intake_deviations)
            avg_intake_dev = sum(intake_deviations) / len(intake_deviations)
            analysis["intake_max_deviation"] = max_intake_dev
            analysis["intake_avg_deviation"] = avg_intake_dev
            
            if max_intake_dev > 5:
                analysis["intake_tracking"] = "Poor"
                analysis["warnings"].append(f"Intake VVT not tracking: {max_intake_dev:.1f}° deviation")
                analysis["recommendations"].append("Check VVT solenoid screens for clogging (common LFX issue)")
            else:
                analysis["intake_tracking"] = "Good"
        
        if exhaust_deviations:
            max_exhaust_dev = max(exhaust_deviations)
            avg_exhaust_dev = sum(exhaust_deviations) / len(exhaust_deviations)
            analysis["exhaust_max_deviation"] = max_exhaust_dev
            analysis["exhaust_avg_deviation"] = avg_exhaust_dev
            
            if max_exhaust_dev > 5:
                analysis["exhaust_tracking"] = "Poor"
                analysis["warnings"].append(f"Exhaust VVT not tracking: {max_exhaust_dev:.1f}° deviation")
            else:
                analysis["exhaust_tracking"] = "Good"
        
        # Overall health
        if analysis["intake_tracking"] == "Good" and analysis["exhaust_tracking"] == "Good":
            analysis["vvt_health"] = "Healthy"
        elif analysis["intake_tracking"] == "Poor" or analysis["exhaust_tracking"] == "Poor":
            analysis["vvt_health"] = "Needs Attention"
        
        return analysis
    
    def generate_stage1_lfx_tune(self, octane_rating: int = 93) -> Dict:
        """Generate Stage 1 tune specifically for LFX Impala"""
        
        tune = {
            "metadata": {
                "platform": "2013 Chevrolet Impala LFX",
                "stage": 1,
                "mods": ["Cold air intake", "Cat-back exhaust"],
                "fuel_requirement": octane_rating,
                "power_estimate": "+12-15 HP"
            },
            "fuel": {
                "maf_scaling": {
                    "description": "Increase 8-12% for CAI",
                    "adjustment": 1.10
                },
                "fuel_mass_wot": {
                    "description": "Richer for power and knock suppression",
                    "stock_afr": 13.2,
                    "tuned_afr": 12.8,
                    "adjustment": "+4%"
                },
                "injector_duty_limit": 85,
                "warning": "Monitor injector duty - LFX near limit with Stage 1"
            },
            "spark": {
                "octane_requirement": octane_rating,
                "timing_changes": {},
                "warning": "12:1 compression is knock-sensitive"
            },
            "vvt": {
                "intake_wot_advance": "+5 degrees from stock",
                "exhaust_wot_retard": "+3 degrees for scavenging",
                "idle_overlap_reduction": "-3 degrees for smoothness"
            },
            "transmission": {
                "shift_points": {
                    "normal": "+400 RPM all gears",
                    "sport": "+500 RPM all gears"
                },
                "line_pressure": 90,
                "torque_management": 95,
                "warning": "6T70 limit ~350 lb-ft"
            }
        }
        
        # Timing based on octane
        if octane_rating >= 93:
            tune["spark"]["timing_changes"] = {
                "wot_timing": "+3-4 degrees if no knock",
                "part_throttle": "+1-2 degrees",
                "cruise": "Stock (economy)"
            }
            tune["spark"]["warning"] = "Use knock sensor data to verify safety"
        else:
            tune["spark"]["timing_changes"] = {
                "wot_timing": "Stock (87 octane limits)",
                "part_throttle": "Stock",
                "cruise": "Stock"
            }
            tune["spark"]["warning"] = "87 octane detected - NO TIMING ADVANCE recommended"
            tune["spark"]["recommendation"] = "Switch to 93 octane for +8-10 HP gain"
        
        return tune
    
    def check_maintenance_items(self, mileage: int) -> List[str]:
        """Check LFX-specific maintenance based on mileage"""
        
        items = []
        
        if mileage > 60000:
            items.append("⚠️ Check for carbon buildup on intake valves ( walnut blasting if rough idle)")
        
        if mileage > 80000:
            items.append("⚠️ Timing chain tensioner wear - listen for rattle on cold start")
            items.append("⚠️ PCV valve check - oil consumption indicates failure")
        
        if mileage > 100000:
            items.append("🔴 High pressure fuel pump (HPFP) failure risk increases - monitor pressure")
            items.append("🔴 VVT solenoid screens likely clogged - clean or replace")
        
        items.append("ℹ️ Verify 5W-30 synthetic oil used (critical for VVT)")
        items.append("ℹ️ Inspect air filter - CAI may need more frequent cleaning")
        
        return items
    
    def pre_tune_checklist(self) -> Dict:
        """LFX-specific checklist before tuning"""
        
        return {
            "mechanical_verification": [
                "Listen for timing chain rattle on cold start (indicates tensioner wear)",
                "Check for oil consumption (PCV failure common)",
                "Verify no coolant in oil or vice versa (head gasket)",
                "Confirm transmission shifts smoothly (6T70 issues)",
                "Check for carbon buildup symptoms (rough idle, especially cold)"
            ],
            "fuel_requirements": [
                "93 octane MINIMUM for any timing advance",
                "87 octane = stock timing only (12:1 compression limited)",
                "Verify fuel station quality (use top tier fuel)"
            ],
            "pre_tuning_logs": [
                "15+ minute drive including WOT acceleration",
                "Monitor HPFP pressure (must maintain 12 MPa at WOT)",
                "Check all 6 cylinders for knock",
                "Verify VVT tracking (commanded vs actual)",
                "Record baseline fuel trims in all cells"
            ],
            "safety_reminders": [
                "Stock tune backup REQUIRED before any changes",
                "LFX cast pistons - detonation risk with bad fuel/timing",
                "HPFP failure = $800+ repair",
                "Injector duty must stay <85%",
                "6T70 transmission limited to ~350 lb-ft"
            ]
        }
    
    def lfx_post_tune_verification(self, log_data: List[Dict]) -> Dict:
        """Comprehensive post-tune verification for LFX"""
        
        results = {
            "fuel_system": self.analyze_lfx_fuel_system(log_data),
            "knock_analysis": self.analyze_lfx_knock(log_data),
            "vvt_health": self.analyze_vvt_operation(log_data),
            "overall_safe": True,
            "can_proceed": True,
            "critical_warnings": []
        }
        
        # Compile critical warnings
        for analysis in [results["fuel_system"], results["knock_analysis"], results["vvt_health"]]:
            if "warnings" in analysis:
                results["critical_warnings"].extend(analysis["warnings"])
        
        # Check if tune is safe
        if not results["fuel_system"].get("can_increase_power", True):
            results["overall_safe"] = False
            results["can_proceed"] = False
        
        if not results["knock_analysis"].get("timing_safe", True):
            results["overall_safe"] = False
            results["can_proceed"] = False
        
        if results["vvt_health"].get("vvt_health") == "Needs Attention":
            results["overall_safe"] = False
            # Don't prevent proceeding but warn
        
        return results
    
    def get_lfx_trans_tuning_advice(self, goal: str = "performance") -> Dict:
        """Get specific 6T70 tuning advice for LFX"""
        
        advice = {
            "transmission": "6T70",
            "torque_limit": "350 lb-ft",
            "engine_limit": "LFX makes ~265 lb-ft stock",
            "headroom": "85 lb-ft before trans limit"
        }
        
        if goal == "performance":
            advice["tune_settings"] = {
                "shift_points": {
                    "normal_1_2": 6400, "normal_2_3": 6200,
                    "sport_1_2": 6800, "sport_2_3": 6700
                },
                "line_pressure": 95,
                "torque_management": 95,
                "shift_firmness": "Medium",
                "notes": "6T70 is comfort-oriented, firm shifts feel sportier"
            }
        elif goal == "daily":
            advice["tune_settings"] = {
                "shift_points": {
                    "normal_1_2": 5800, "normal_2_3": 5600,
                    "sport_1_2": 6200, "sport_2_3": 6000
                },
                "line_pressure": 85,
                "torque_management": 100,
                "shift_firmness": "Stock",
                "notes": "Keep stock feel for comfort, just raise shifts slightly"
            }
        elif goal == "mpg":
            advice["tune_settings"] = {
                "shift_points": {
                    "normal_1_2": 5200, "normal_2_3": 5000
                },
                "line_pressure": 80,
                "tc_lockup": "Enable in 1st gear for highway (harsh but efficient)",
                "notes": "Lower line pressure for efficiency, earlier shifts"
            }
        
        return advice


# Example usage and testing
if __name__ == "__main__":
    print("LFX Impala Controller Module")
    print("============================")
    print()
    print("This module provides LFX-specific tuning capabilities")
    print()
    
    # Show PID list
    print("LFX-Specific PIDs Required:")
    controller = LFXImpalaController(None)
    pids = controller.get_lfx_logging_pids()
    
    print("\nStandard PIDs:")
    for pid in pids[:12]:
        print(f"  - {pid}")
    
    print("\nLFX-Specific PIDs:")
    for pid in pids[12:]:
        print(f"  - {pid}")
    
    print("\nStage 1 Tune Template (93 octane):")
    tune = controller.generate_stage1_lfx_tune(octane_rating=93)
    print(json.dumps(tune, indent=2))
    
    print("\nPre-Tune Checklist:")
    checklist = controller.pre_tune_checklist()
    for category, items in checklist.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for item in items:
            print(f"  ☐ {item}")
    
    print("\nMaintenance Check (80,000 miles):")
    maintenance = controller.check_maintenance_items(80000)
    for item in maintenance:
        print(f"  {item}")