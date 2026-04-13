#!/usr/bin/env python3
"""
VCM Scanner Data Import and Analysis
Parses CSV/LOG files exported from HP Tuners VCM Scanner
"""

import csv
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class LoggedParameter:
    """Single parameter reading"""
    name: str
    value: float
    unit: str
    timestamp: float
    
    
@dataclass
class LogSession:
    """Complete logging session"""
    filename: str
    start_time: datetime
    vehicle_info: Dict
    parameters: List[str]
    data: List[Dict[str, any]] = field(default_factory=list)
    
    def get_parameter(self, name: str) -> List[float]:
        """Extract all values for a parameter"""
        return [row.get(name) for row in self.data if name in row and row[name] is not None]
        
    def get_time_series(self, name: str) -> List[Tuple[float, float]]:
        """Get parameter as (time, value) pairs"""
        return [(row.get('Time', i), row.get(name)) 
                for i, row in enumerate(self.data) 
                if name in row and row[name] is not None]


class VCMScannerImporter:
    """
    Import and analyze VCM Scanner CSV files
    """
    
    # Standard HP Tuners PID names
    PID_MAPPINGS = {
        # Engine
        "Engine RPM": "RPM",
        "Engine Speed": "RPM", 
        "Vehicle Speed": "SPEED",
        "Calculated Load": "ENGINE_LOAD",
        "Throttle Position": "THROTTLE_POS",
        "Absolute Throttle Position B": "THROTTLE_POS_B",
        "Accelerator Pedal Position D": "PEDAL_POS",
        
        # Fuel
        "Mass Air Flow": "MAF",
        "MAF Frequency": "MAF_FREQ",
        "Fuel Trim Cell": "FUEL_TRIM_CELL",
        "Short Term Fuel Trim Bank 1": "STFT_B1",
        "Long Term Fuel Trim Bank 1": "LTFT_B1",
        "Short Term Fuel Trim Bank 2": "STFT_B2",
        "Long Term Fuel Trim Bank 2": "LTFT_B2",
        "Commanded Equivalence Ratio": "LAMBDA_CMD",
        "O2 Sensor 1 Bank 1": "O2_B1S1",
        "O2 Sensor 2 Bank 1": "O2_B1S2",
        "O2 Sensor 1 Bank 2": "O2_B2S1",
        "Fuel Level": "FUEL_LEVEL",
        "Fuel Tank Pressure": "FUEL_TANK_PRESSURE",
        "Fuel Rail Pressure": "FUEL_RAIL_PRESSURE",
        "High Pressure Fuel Pump": "HPFP_PRESSURE",
        
        # Spark
        "Spark Advance": "SPARK_ADV",
        "Ignition Timing": "SPARK_ADV",
        "Knock Retard": "KNOCK_RETARD",
        "Knock Sensor 1": "KNOCK_1",
        "Knock Sensor 2": "KNOCK_2",
        "Knock Sensor 3": "KNOCK_3",
        "Knock Sensor 4": "KNOCK_4",
        
        # Temps
        "Engine Coolant Temperature": "COOLANT_TEMP",
        "Intake Air Temperature": "INTAKE_TEMP",
        "Ambient Air Temperature": "AMBIENT_TEMP",
        "Transmission Fluid Temperature": "TRANS_TEMP",
        "Engine Oil Temperature": "OIL_TEMP",
        "Cylinder Head Temperature": "CHT",
        
        # Airflow
        "Manifold Absolute Pressure": "MAP",
        "Barometric Pressure": "BARO",
        "Volumetric Efficiency": "VE",
        
        # VVT
        "Intake Cam Position": "VVT_INTAKE",
        "Exhaust Cam Position": "VVT_EXHAUST",
        "Cam Phase Angle": "CAM_PHASE",
        
        # Transmission
        "Transmission Gear": "GEAR",
        "Commanded Gear": "GEAR_CMD",
        "TCC Slip": "TCC_SLIP",
        "TCC Command": "TCC_CMD",
        "Line Pressure": "LINE_PRESSURE",
        "Shift Time": "SHIFT_TIME",
        "Transmission Input Speed": "TURBINE_SPEED",
        "Transmission Output Speed": "OUTPUT_SPEED",
        
        # Torque
        "Engine Torque": "ENGINE_TORQUE",
        "Driver Requested Torque": "TORQUE_REQ",
        "Maximum Torque": "TORQUE_MAX",
        
        # Electrical
        "Battery Voltage": "BATTERY_VOLTAGE",
        "Alternator Command": "ALTERNATOR_CMD",
        
        # Boost (turbo/supercharged)
        "Boost Pressure": "BOOST",
        "Desired Boost": "BOOST_CMD",
        "Wastegate Duty": "WASTEGATE",
        
        # Other
        "Run Time": "RUN_TIME",
        "Distance Traveled": "DISTANCE",
        "Miles Since DTC Cleared": "MILES_SINCE_DTC"
    }
    
    def __init__(self):
        self.sessions: List[LogSession] = []
        
    def import_csv(self, filepath: Path) -> LogSession:
        """Import a VCM Scanner CSV export"""
        filepath = Path(filepath)
        
        with open(filepath, 'r', newline='') as f:
            # Detect dialect
            sample = f.read(8192)
            f.seek(0)
            
            # Try to read header
            reader = csv.reader(f)
            header = next(reader)
            
            # Normalize column names
            normalized_header = []
            for col in header:
                # Remove units in parentheses
                col_clean = col.split('(')[0].strip()
                # Map to standard name
                mapped = self.PID_MAPPINGS.get(col_clean, col_clean)
                normalized_header.append(mapped)
                
            # Read data
            data = []
            for row in reader:
                if not row:
                    continue
                entry = {}
                for i, value in enumerate(row):
                    if i < len(normalized_header):
                        col_name = normalized_header[i]
                        # Try to convert to number
                        try:
                            entry[col_name] = float(value)
                        except (ValueError, TypeError):
                            entry[col_name] = value
                data.append(entry)
                
        session = LogSession(
            filename=filepath.name,
            start_time=datetime.now(),  # Could parse from filename
            vehicle_info={},
            parameters=normalized_header,
            data=data
        )
        
        self.sessions.append(session)
        logger.info(f"Imported {len(data)} rows from {filepath}")
        return session
        
    def import_multiple(self, filepaths: List[Path]) -> List[LogSession]:
        """Import multiple CSV files"""
        return [self.import_csv(fp) for fp in filepaths]


class LogAnalyzer:
    """Analyze VCM Scanner log data"""
    
    def __init__(self, session: LogSession):
        self.session = session
        
    def find_wot_events(self, tps_threshold: float = 90.0, 
                        min_duration: float = 1.0) -> List[Dict]:
        """Find Wide Open Throttle acceleration events"""
        events = []
        in_wot = False
        event_start = 0
        event_data = []
        
        for i, row in enumerate(self.session.data):
            tps = row.get('THROTTLE_POS') or row.get('PEDAL_POS', 0)
            
            if tps >= tps_threshold and not in_wot:
                in_wot = True
                event_start = i
                event_data = [row]
            elif tps >= tps_threshold and in_wot:
                event_data.append(row)
            elif tps < tps_threshold - 10 and in_wot:
                in_wot = False
                duration = len(event_data) * 0.1  # Approximate
                if duration >= min_duration:
                    events.append({
                        'start_idx': event_start,
                        'end_idx': i,
                        'duration': duration,
                        'data': event_data,
                        'max_rpm': max(r.get('RPM', 0) for r in event_data),
                        'max_speed': max(r.get('SPEED', 0) for r in event_data)
                    })
                    
        return events
        
    def analyze_fuel_trims(self) -> Dict:
        """Analyze fuel trim behavior"""
        stft_b1 = self.session.get_parameter('STFT_B1')
        ltft_b1 = self.session.get_parameter('LTFT_B1')
        
        if not stft_b1:
            return {"error": "No fuel trim data available"}
            
        analysis = {
            "stft_avg": sum(stft_b1) / len(stft_b1) if stft_b1 else 0,
            "stft_min": min(stft_b1) if stft_b1 else 0,
            "stft_max": max(stft_b1) if stft_b1 else 0,
            "ltft_avg": sum(ltft_b1) / len(ltft_b1) if ltft_b1 else 0,
            "correction_needed": False,
            "recommendation": ""
        }
        
        # Evaluate
        if abs(analysis["stft_avg"]) < 3:
            analysis["recommendation"] = "✓ Fuel trims optimal"
        elif analysis["stft_avg"] > 5:
            analysis["recommendation"] = f"⚠ Running lean (+{analysis['stft_avg']:.1f}%) - increase fuel mass"
            analysis["correction_needed"] = True
        elif analysis["stft_avg"] < -5:
            analysis["recommendation"] = f"⚠ Running rich ({analysis['stft_avg']:.1f}%) - decrease fuel mass"
            analysis["correction_needed"] = True
            
        return analysis
        
    def analyze_knock(self) -> Dict:
        """Analyze knock sensor data"""
        knock_data = self.session.get_parameter('KNOCK_RETARD')
        
        if not knock_data:
            return {"error": "No knock retard data available"}
            
        events = [k for k in knock_data if k > 0]
        rpm_data = self.session.get_parameter('RPM')
        
        analysis = {
            "total_events": len(events),
            "max_retard": max(knock_data) if knock_data else 0,
            "avg_retard": sum(events) / len(events) if events else 0,
            "event_percentage": len(events) / len(knock_data) * 100 if knock_data else 0,
            "severity": "none"
        }
        
        # Categorize severity
        if analysis["max_retard"] > 8:
            analysis["severity"] = "CRITICAL"
        elif analysis["max_retard"] > 4:
            analysis["severity"] = "HIGH"
        elif analysis["max_retard"] > 2:
            analysis["severity"] = "MODERATE"
        elif analysis["max_retard"] > 0:
            analysis["severity"] = "LOW"
            
        return analysis
        
    def analyze_transmission(self) -> Dict:
        """Analyze transmission behavior"""
        gear_data = self.session.get_parameter('GEAR')
        slip_data = self.session.get_parameter('TCC_SLIP')
        temp_data = self.session.get_parameter('TRANS_TEMP')
        
        analysis = {
            "gear_changes": 0,
            "max_slip": 0,
            "avg_temp": 0,
            "shifts": []
        }
        
        if gear_data:
            # Count gear changes
            prev_gear = gear_data[0]
            for g in gear_data[1:]:
                if g != prev_gear:
                    analysis["gear_changes"] += 1
                    analysis["shifts"].append({"from": prev_gear, "to": g})
                prev_gear = g
                
        if slip_data:
            analysis["max_slip"] = max(slip_data)
            
        if temp_data:
            analysis["avg_temp"] = sum(temp_data) / len(temp_data)
            
        return analysis
        
    def generate_summary(self) -> Dict:
        """Generate complete log summary"""
        rpm_data = self.session.get_parameter('RPM')
        speed_data = self.session.get_parameter('SPEED')
        
        summary = {
            "file": self.session.filename,
            "duration_samples": len(self.session.data),
            "rpm_range": {
                "min": min(rpm_data) if rpm_data else 0,
                "max": max(rpm_data) if rpm_data else 0,
                "avg": sum(rpm_data) / len(rpm_data) if rpm_data else 0
            },
            "speed_range": {
                "min": min(speed_data) if speed_data else 0,
                "max": max(speed_data) if speed_data else 0
            },
            "fuel_analysis": self.analyze_fuel_trims(),
            "knock_analysis": self.analyze_knock(),
            "trans_analysis": self.analyze_transmission(),
            "wot_events": len(self.find_wot_events())
        }
        
        return summary


class TuneRecommendationEngine:
    """Generate tuning recommendations based on log analysis"""
    
    def __init__(self, analyzer: LogAnalyzer):
        self.analyzer = analyzer
        
    def generate_recommendations(self) -> List[Dict]:
        """Generate actionable tuning recommendations"""
        recommendations = []
        
        # Fuel analysis
        fuel = self.analyzer.analyze_fuel_trims()
        if fuel.get("correction_needed"):
            if fuel["stft_avg"] > 5:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Fuel",
                    "issue": "Lean condition detected",
                    "detail": f"STFT averaging +{fuel['stft_avg']:.1f}%",
                    "action": "Increase fuel mass 4-6% in affected cells",
                    "tables": ["Base Fuel Mass", "MAF Calibration"]
                })
            elif fuel["stft_avg"] < -5:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Fuel",
                    "issue": "Rich condition detected",
                    "detail": f"STFT averaging {fuel['stft_avg']:.1f}%",
                    "action": "Decrease fuel mass 4-6% in affected cells",
                    "tables": ["Base Fuel Mass", "MAF Calibration"]
                })
                
        # Knock analysis
        knock = self.analyzer.analyze_knock()
        if knock.get("max_retard", 0) > 4:
            recommendations.append({
                "priority": "CRITICAL" if knock["max_retard"] > 8 else "HIGH",
                "category": "Spark",
                "issue": f"Knock detected (max {knock['max_retard']:.1f}° retard)",
                "detail": f"{knock['total_events']} knock events",
                "action": "Reduce spark advance 2-4° in affected RPM/load range",
                "tables": ["Spark Advance", "Knock Retard"]
            })
            
        # WOT analysis
        wot_events = self.analyzer.find_wot_events()
        if not wot_events:
            recommendations.append({
                "priority": "INFO",
                "category": "Logging",
                "issue": "No WOT events detected",
                "detail": "Need WOT data for complete tune",
                "action": "Perform WOT acceleration from 2500-6500 RPM and re-log"
            })
        else:
            recommendations.append({
                "priority": "INFO",
                "category": "Data",
                "issue": f"Found {len(wot_events)} WOT events",
                "detail": f"Max RPM: {max(e['max_rpm'] for e in wot_events):.0f}",
                "action": "Analyze WOT AFR and timing if wideband installed"
            })
            
        return sorted(recommendations, key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].index(x.get("priority", "INFO")))


# Example usage
if __name__ == "__main__":
    # Example: Import and analyze a log file
    importer = VCMScannerImporter()
    
    # Create sample data for demonstration
    sample_data = [
        {"RPM": 750, "THROTTLE_POS": 0, "STFT_B1": 2.5, "KNOCK_RETARD": 0},
        {"RPM": 1500, "THROTTLE_POS": 25, "STFT_B1": 3.0, "KNOCK_RETARD": 0},
        {"RPM": 2500, "THROTTLE_POS": 50, "STFT_B1": 4.5, "KNOCK_RETARD": 0},
        {"RPM": 4000, "THROTTLE_POS": 100, "STFT_B1": 8.0, "KNOCK_RETARD": 0},
        {"RPM": 5500, "THROTTLE_POS": 100, "STFT_B1": 9.5, "KNOCK_RETARD": 2.5},
        {"RPM": 6000, "THROTTLE_POS": 100, "STFT_B1": 10.0, "KNOCK_RETARD": 4.0},
    ]
    
    session = LogSession(
        filename="sample.csv",
        start_time=datetime.now(),
        vehicle_info={},
        parameters=["RPM", "THROTTLE_POS", "STFT_B1", "KNOCK_RETARD"],
        data=sample_data
    )
    
    analyzer = LogAnalyzer(session)
    summary = analyzer.generate_summary()
    print(json.dumps(summary, indent=2))
    
    engine = TuneRecommendationEngine(analyzer)
    recs = engine.generate_recommendations()
    print("\nRecommendations:")
    for r in recs:
        print(f"[{r['priority']}] {r['category']}: {r['issue']}")
        print(f"  → {r['action']}")
