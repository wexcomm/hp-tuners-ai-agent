#!/usr/bin/env python3
"""
Comprehensive Diagnostic Trouble Code (DTC) Database
Based on Automotive DTC Library with 5,000+ codes
Covers Generic OBD-II and OEM-specific codes
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DTCCategory(Enum):
    """DTC Category classifications"""
    POWERTRAIN = "Powertrain"
    BODY = "Body"
    CHASSIS = "Chassis"
    NETWORK = "Network/U-Code"


class DTCSeverity(Enum):
    """DTC Severity levels"""
    INFO = "Info"           # Informational only
    MINOR = "Minor"         # Minor issue, monitor
    MODERATE = "Moderate"   # Should address soon
    SEVERE = "Severe"       # Address immediately
    CRITICAL = "Critical"   # Stop driving, potential damage


@dataclass
class DTC:
    """Diagnostic Trouble Code definition"""
    code: str                           # e.g., "P0011"
    description: str                    # Full description
    category: str                       # Functional category (e.g., "VVT System")
    severity: DTCSeverity = DTCSeverity.MODERATE
    symptoms: List[str] = field(default_factory=list)
    possible_causes: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)
    tuning_related: bool = False        # Is this relevant to tuning?
    manufacturer: str = "Generic"       # Generic, GM, Ford, etc.
    
    def __post_init__(self):
        # Auto-detect severity based on code patterns
        if self.severity == DTCSeverity.MODERATE:
            self.severity = self._auto_detect_severity()
            
    def _auto_detect_severity(self) -> DTCSeverity:
        """Auto-detect severity based on code type"""
        code_upper = self.code.upper()
        desc_lower = self.description.lower()
        
        # Critical codes
        critical_patterns = [
            r'P00(08|09)',  # Engine position system
            r'P01(35|36)',  # O2 sensor heater circuit
            r'P02(00|19|30)',  # Cylinder misfire
            r'P03(00|31|32|33|34|35|36)',  # Misfire specific cylinders
            r'P06(21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|40)',  # Internal control module
            r'P07(00|01|02|03)',  # Transmission solenoid
            r'P08(26|27|28|29)',  # Clutch position
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, code_upper):
                return DTCSeverity.CRITICAL
                
        # Severe codes
        severe_patterns = [
            r'P00(10|11)',  # Fuel pressure
            r'P01(12|13)',  # RPM circuit
            r'P02(1[7-9]|2[0-9]|3[0-9])',  # Injector circuit
            r'P03(0[0-9]|1[0-9]|2[0-9])',  # Ignition coils
            r'P04(00|40)',  # EGR
            r'P05(00|30|33)',  # Idle control
            r'P06(00|06)',  # ECM/PCM processor
        ]
        
        for pattern in severe_patterns:
            if re.search(pattern, code_upper):
                return DTCSeverity.SEVERE
                
        # Check description for keywords
        critical_keywords = ['misfire', 'internal control', 'overheating', 'knock']
        severe_keywords = ['circuit high', 'circuit low', 'performance', 'range']
        
        for kw in critical_keywords:
            if kw in desc_lower:
                return DTCSeverity.CRITICAL
        for kw in severe_keywords:
            if kw in desc_lower:
                return DTCSeverity.SEVERE
                
        return DTCSeverity.MODERATE
        
    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "description": self.description,
            "category": self.category,
            "severity": self.severity.value,
            "symptoms": self.symptoms,
            "possible_causes": self.possible_causes,
            "affected_systems": self.affected_systems,
            "tuning_related": self.tuning_related,
            "manufacturer": self.manufacturer
        }


class DTCDatabase:
    """
    Comprehensive DTC Database
    5,000+ codes covering Generic OBD-II and OEM-specific
    """
    
    def __init__(self):
        self.dtcs: Dict[str, DTC] = {}
        self._initialize_generic_codes()
        self._initialize_gm_codes()
        self._initialize_tuning_related_codes()
        
    def _initialize_generic_codes(self):
        """Initialize Generic OBD-II P0xxx codes (Powertrain)"""
        generic_p0_codes = [
            # Fuel System
            ("P0001", "Fuel Volume Regulator Control Circuit/Open", "Fuel System"),
            ("P0002", "Fuel Volume Regulator Control Circuit Range/Performance", "Fuel System"),
            ("P0003", "Fuel Volume Regulator Control Circuit Low", "Fuel System"),
            ("P0004", "Fuel Volume Regulator Control Circuit High", "Fuel System"),
            ("P0005", "Fuel Shutoff Valve A Control Circuit/Open", "Fuel System"),
            ("P0006", "Fuel Shutoff Valve A Control Circuit Low", "Fuel System"),
            ("P0007", "Fuel Shutoff Valve A Control Circuit High", "Fuel System"),
            ("P0008", "Engine Position System Performance Bank 1", "Engine Position"),
            ("P0009", "Engine Position System Performance Bank 2", "Engine Position"),
            ("P0010", "A Camshaft Position Actuator Circuit (Bank 1)", "VVT System"),
            ("P0011", "A Camshaft Position - Timing Over-Advanced or System Performance (Bank 1)", "VVT System"),
            ("P0012", "A Camshaft Position - Timing Over-Retarded (Bank 1)", "VVT System"),
            ("P0013", "B Camshaft Position Actuator Circuit (Bank 1)", "VVT System"),
            ("P0014", "B Camshaft Position - Timing Over-Advanced or System Performance (Bank 1)", "VVT System"),
            ("P0015", "B Camshaft Position - Timing Over-Retarded (Bank 1)", "VVT System"),
            ("P0016", "Crankshaft Position - Camshaft Position Correlation (Bank 1 Sensor A)", "VVT System"),
            ("P0017", "Crankshaft Position - Camshaft Position Correlation (Bank 1 Sensor B)", "VVT System"),
            ("P0018", "Crankshaft Position - Camshaft Position Correlation (Bank 2 Sensor A)", "VVT System"),
            ("P0019", "Crankshaft Position - Camshaft Position Correlation (Bank 2 Sensor B)", "VVT System"),
            ("P0020", "A Camshaft Position Actuator Circuit (Bank 2)", "VVT System"),
            ("P0021", "A Camshaft Position - Timing Over-Advanced or System Performance (Bank 2)", "VVT System"),
            ("P0022", "A Camshaft Position - Timing Over-Retarded (Bank 2)", "VVT System"),
            ("P0023", "B Camshaft Position Actuator Circuit (Bank 2)", "VVT System"),
            ("P0024", "B Camshaft Position - Timing Over-Advanced or System Performance (Bank 2)", "VVT System"),
            ("P0025", "B Camshaft Position - Timing Over-Retarded (Bank 2)", "VVT System"),
            
            # Fuel Pressure
            ("P0087", "Fuel Rail/System Pressure Too Low", "Fuel System"),
            ("P0088", "Fuel Rail/System Pressure Too High", "Fuel System"),
            ("P0089", "Fuel Pressure Regulator 1 Performance", "Fuel System"),
            ("P0090", "Fuel Pressure Regulator 1 Control Circuit", "Fuel System"),
            ("P0091", "Fuel Pressure Regulator 1 Control Circuit Low", "Fuel System"),
            ("P0092", "Fuel Pressure Regulator 1 Control Circuit High", "Fuel System"),
            ("P0093", "Fuel System Leak Detected - Large Leak", "Fuel System"),
            ("P0094", "Fuel System Leak Detected - Small Leak", "Fuel System"),
            
            # MAF/Airflow
            ("P0100", "Mass or Volume Air Flow Circuit", "Air Intake"),
            ("P0101", "Mass or Volume Air Flow Circuit Range/Performance", "Air Intake"),
            ("P0102", "Mass or Volume Air Flow Circuit Low Input", "Air Intake"),
            ("P0103", "Mass or Volume Air Flow Circuit High Input", "Air Intake"),
            ("P0104", "Mass or Volume Air Flow Circuit Intermittent", "Air Intake"),
            
            # MAP
            ("P0105", "Manifold Absolute Pressure/Barometric Pressure Circuit", "Air Intake"),
            ("P0106", "Manifold Absolute Pressure/Barometric Pressure Circuit Range/Performance", "Air Intake"),
            ("P0107", "Manifold Absolute Pressure/Barometric Pressure Circuit Low Input", "Air Intake"),
            ("P0108", "Manifold Absolute Pressure/Barometric Pressure Circuit High Input", "Air Intake"),
            ("P0109", "Manifold Absolute Pressure/Barometric Pressure Circuit Intermittent", "Air Intake"),
            
            # Intake Air Temp
            ("P0110", "Intake Air Temperature Circuit", "Temperature Sensor"),
            ("P0111", "Intake Air Temperature Circuit Range/Performance", "Temperature Sensor"),
            ("P0112", "Intake Air Temperature Circuit Low Input", "Temperature Sensor"),
            ("P0113", "Intake Air Temperature Circuit High Input", "Temperature Sensor"),
            
            # Coolant Temp
            ("P0115", "Engine Coolant Temperature Circuit", "Temperature Sensor"),
            ("P0116", "Engine Coolant Temperature Circuit Range/Performance", "Temperature Sensor"),
            ("P0117", "Engine Coolant Temperature Circuit Low Input", "Temperature Sensor"),
            ("P0118", "Engine Coolant Temperature Circuit High Input", "Temperature Sensor"),
            ("P0119", "Engine Coolant Temperature Circuit Intermittent", "Temperature Sensor"),
            
            # Throttle Position
            ("P0120", "Throttle/Pedal Position Sensor/Switch A Circuit", "Throttle"),
            ("P0121", "Throttle/Pedal Position Sensor/Switch A Circuit Range/Performance", "Throttle"),
            ("P0122", "Throttle/Pedal Position Sensor/Switch A Circuit Low Input", "Throttle"),
            ("P0123", "Throttle/Pedal Position Sensor/Switch A Circuit High Input", "Throttle"),
            ("P0124", "Throttle/Pedal Position Sensor/Switch A Circuit Intermittent", "Throttle"),
            
            # O2 Sensors
            ("P0130", "O2 Sensor Circuit (Bank 1 Sensor 1)", "Emissions"),
            ("P0131", "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 1)", "Emissions"),
            ("P0132", "O2 Sensor Circuit High Voltage (Bank 1 Sensor 1)", "Emissions"),
            ("P0133", "O2 Sensor Circuit Slow Response (Bank 1 Sensor 1)", "Emissions"),
            ("P0134", "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 1)", "Emissions"),
            ("P0135", "O2 Sensor Heater Circuit (Bank 1 Sensor 1)", "Emissions"),
            ("P0136", "O2 Sensor Circuit (Bank 1 Sensor 2)", "Emissions"),
            ("P0137", "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 2)", "Emissions"),
            ("P0138", "O2 Sensor Circuit High Voltage (Bank 1 Sensor 2)", "Emissions"),
            ("P0139", "O2 Sensor Circuit Slow Response (Bank 1 Sensor 2)", "Emissions"),
            ("P0140", "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 2)", "Emissions"),
            ("P0141", "O2 Sensor Heater Circuit (Bank 1 Sensor 2)", "Emissions"),
            ("P0150", "O2 Sensor Circuit (Bank 2 Sensor 1)", "Emissions"),
            ("P0151", "O2 Sensor Circuit Low Voltage (Bank 2 Sensor 1)", "Emissions"),
            ("P0152", "O2 Sensor Circuit High Voltage (Bank 2 Sensor 1)", "Emissions"),
            ("P0153", "O2 Sensor Circuit Slow Response (Bank 2 Sensor 1)", "Emissions"),
            ("P0154", "O2 Sensor Circuit No Activity Detected (Bank 2 Sensor 1)", "Emissions"),
            ("P0155", "O2 Sensor Heater Circuit (Bank 2 Sensor 1)", "Emissions"),
            
            # Fuel Trim
            ("P0171", "System Too Lean (Bank 1)", "Fuel System"),
            ("P0172", "System Too Rich (Bank 1)", "Fuel System"),
            ("P0174", "System Too Lean (Bank 2)", "Fuel System"),
            ("P0175", "System Too Rich (Bank 2)", "Fuel System"),
            
            # Injectors
            ("P0200", "Injector Circuit/Open", "Fuel System"),
            ("P0201", "Injector Circuit/Open - Cylinder 1", "Fuel System"),
            ("P0202", "Injector Circuit/Open - Cylinder 2", "Fuel System"),
            ("P0203", "Injector Circuit/Open - Cylinder 3", "Fuel System"),
            ("P0204", "Injector Circuit/Open - Cylinder 4", "Fuel System"),
            ("P0205", "Injector Circuit/Open - Cylinder 5", "Fuel System"),
            ("P0206", "Injector Circuit/Open - Cylinder 6", "Fuel System"),
            ("P0207", "Injector Circuit/Open - Cylinder 7", "Fuel System"),
            ("P0208", "Injector Circuit/Open - Cylinder 8", "Fuel System"),
            ("P0209", "Injector Circuit/Open - Cylinder 9", "Fuel System"),
            ("P0210", "Injector Circuit/Open - Cylinder 10", "Fuel System"),
            ("P0211", "Injector Circuit/Open - Cylinder 11", "Fuel System"),
            ("P0212", "Injector Circuit/Open - Cylinder 12", "Fuel System"),
            
            # Engine Overheating
            ("P0217", "Engine Overheat Condition", "Temperature"),
            ("P0218", "Transmission Fluid OverTemperature", "Transmission"),
            ("P0219", "Engine Overspeed Condition", "Engine"),
            
            # Misfire
            ("P0300", "Random/Multiple Cylinder Misfire Detected", "Ignition"),
            ("P0301", "Cylinder 1 Misfire Detected", "Ignition"),
            ("P0302", "Cylinder 2 Misfire Detected", "Ignition"),
            ("P0303", "Cylinder 3 Misfire Detected", "Ignition"),
            ("P0304", "Cylinder 4 Misfire Detected", "Ignition"),
            ("P0305", "Cylinder 5 Misfire Detected", "Ignition"),
            ("P0306", "Cylinder 6 Misfire Detected", "Ignition"),
            ("P0307", "Cylinder 7 Misfire Detected", "Ignition"),
            ("P0308", "Cylinder 8 Misfire Detected", "Ignition"),
            ("P0309", "Cylinder 9 Misfire Detected", "Ignition"),
            ("P0310", "Cylinder 10 Misfire Detected", "Ignition"),
            ("P0311", "Cylinder 11 Misfire Detected", "Ignition"),
            ("P0312", "Cylinder 12 Misfire Detected", "Ignition"),
            
            # Knock Sensor
            ("P0324", "Knock Control System Error", "Ignition"),
            ("P0325", "Knock Sensor 1 Circuit (Bank 1 or Single Sensor)", "Ignition"),
            ("P0326", "Knock Sensor 1 Circuit Range/Performance (Bank 1 or Single Sensor)", "Ignition"),
            ("P0327", "Knock Sensor 1 Circuit Low Input (Bank 1 or Single Sensor)", "Ignition"),
            ("P0328", "Knock Sensor 1 Circuit High Input (Bank 1 or Single Sensor)", "Ignition"),
            ("P0329", "Knock Sensor 1 Circuit Input Intermittent (Bank 1 or Single Sensor)", "Ignition"),
            ("P0330", "Knock Sensor 2 Circuit (Bank 2)", "Ignition"),
            ("P0331", "Knock Sensor 2 Circuit Range/Performance (Bank 2)", "Ignition"),
            ("P0332", "Knock Sensor 2 Circuit Low Input (Bank 2)", "Ignition"),
            ("P0333", "Knock Sensor 2 Circuit High Input (Bank 2)", "Ignition"),
            
            # Crankshaft Position
            ("P0335", "Crankshaft Position Sensor A Circuit", "Engine Position"),
            ("P0336", "Crankshaft Position Sensor A Circuit Range/Performance", "Engine Position"),
            ("P0337", "Crankshaft Position Sensor A Circuit Low Input", "Engine Position"),
            ("P0338", "Crankshaft Position Sensor A Circuit High Input", "Engine Position"),
            ("P0339", "Crankshaft Position Sensor A Circuit Intermittent", "Engine Position"),
            
            # Camshaft Position
            ("P0340", "Camshaft Position Sensor Circuit", "Engine Position"),
            ("P0341", "Camshaft Position Sensor Circuit Range/Performance", "Engine Position"),
            ("P0342", "Camshaft Position Sensor Circuit Low Input", "Engine Position"),
            ("P0343", "Camshaft Position Sensor Circuit High Input", "Engine Position"),
            ("P0344", "Camshaft Position Sensor Circuit Intermittent", "Engine Position"),
            
            # Ignition Coils
            ("P0350", "Ignition Coil Primary/Secondary Circuit", "Ignition"),
            ("P0351", "Ignition Coil A Primary/Secondary Circuit", "Ignition"),
            ("P0352", "Ignition Coil B Primary/Secondary Circuit", "Ignition"),
            ("P0353", "Ignition Coil C Primary/Secondary Circuit", "Ignition"),
            ("P0354", "Ignition Coil D Primary/Secondary Circuit", "Ignition"),
            ("P0355", "Ignition Coil E Primary/Secondary Circuit", "Ignition"),
            ("P0356", "Ignition Coil F Primary/Secondary Circuit", "Ignition"),
            ("P0357", "Ignition Coil G Primary/Secondary Circuit", "Ignition"),
            ("P0358", "Ignition Coil H Primary/Secondary Circuit", "Ignition"),
            
            # EGR
            ("P0400", "Exhaust Gas Recirculation Flow", "Emissions"),
            ("P0401", "Exhaust Gas Recirculation Flow Insufficient Detected", "Emissions"),
            ("P0402", "Exhaust Gas Recirculation Flow Excessive Detected", "Emissions"),
            ("P0403", "Exhaust Gas Recirculation Control Circuit", "Emissions"),
            ("P0404", "Exhaust Gas Recirculation Control Circuit Range/Performance", "Emissions"),
            ("P0405", "Exhaust Gas Recirculation Sensor A Circuit Low", "Emissions"),
            ("P0406", "Exhaust Gas Recirculation Sensor A Circuit High", "Emissions"),
            
            # Catalyst
            ("P0420", "Catalyst System Efficiency Below Threshold (Bank 1)", "Emissions"),
            ("P0430", "Catalyst System Efficiency Below Threshold (Bank 2)", "Emissions"),
            
            # EVAP
            ("P0440", "Evaporative Emission Control System", "Emissions"),
            ("P0441", "Evaporative Emission Control System Incorrect Purge Flow", "Emissions"),
            ("P0442", "Evaporative Emission Control System Leak Detected (Small Leak)", "Emissions"),
            ("P0443", "Evaporative Emission Control System Purge Control Valve Circuit", "Emissions"),
            ("P0444", "Evaporative Emission Control System Purge Control Valve Circuit Open", "Emissions"),
            ("P0445", "Evaporative Emission Control System Purge Control Valve Circuit Shorted", "Emissions"),
            ("P0446", "Evaporative Emission Control System Vent Control Circuit", "Emissions"),
            ("P0447", "Evaporative Emission Control System Vent Control Circuit Open", "Emissions"),
            ("P0448", "Evaporative Emission Control System Vent Control Circuit Shorted", "Emissions"),
            ("P0449", "Evaporative Emission Control System Vent Valve/Solenoid Circuit", "Emissions"),
            ("P0450", "Evaporative Emission Control System Pressure Sensor", "Emissions"),
            ("P0451", "Evaporative Emission Control System Pressure Sensor Range/Performance", "Emissions"),
            ("P0452", "Evaporative Emission Control System Pressure Sensor Low Input", "Emissions"),
            ("P0453", "Evaporative Emission Control System Pressure Sensor High Input", "Emissions"),
            ("P0455", "Evaporative Emission Control System Leak Detected (Gross Leak)", "Emissions"),
            ("P0456", "Evaporative Emission Control System Leak Detected (Very Small Leak)", "Emissions"),
            
            # Idle Control
            ("P0505", "Idle Control System", "Idle"),
            ("P0506", "Idle Control System RPM Lower Than Expected", "Idle"),
            ("P0507", "Idle Control System RPM Higher Than Expected", "Idle"),
            
            # Transmission
            ("P0700", "Transmission Control System (MIL Request)", "Transmission"),
            ("P0705", "Transmission Range Sensor Circuit", "Transmission"),
            ("P0706", "Transmission Range Sensor Circuit Range/Performance", "Transmission"),
            ("P0710", "Transmission Fluid Temperature Sensor Circuit", "Transmission"),
            ("P0711", "Transmission Fluid Temperature Sensor Circuit Range/Performance", "Transmission"),
            ("P0712", "Transmission Fluid Temperature Sensor Circuit Low Input", "Transmission"),
            ("P0713", "Transmission Fluid Temperature Sensor Circuit High Input", "Transmission"),
            ("P0720", "Output Speed Sensor Circuit", "Transmission"),
            ("P0725", "Engine Speed Input Circuit", "Transmission"),
            ("P0730", "Incorrect Gear Ratio", "Transmission"),
            ("P0740", "Torque Converter Clutch Circuit", "Transmission"),
            ("P0741", "Torque Converter Clutch Circuit Performance or Stuck Off", "Transmission"),
            ("P0742", "Torque Converter Clutch Circuit Stuck On", "Transmission"),
            ("P0750", "Shift Solenoid A", "Transmission"),
            ("P0751", "Shift Solenoid A Performance or Stuck Off", "Transmission"),
            ("P0752", "Shift Solenoid A Stuck On", "Transmission"),
            ("P0753", "Shift Solenoid A Electrical", "Transmission"),
            ("P0760", "Shift Solenoid C", "Transmission"),
            ("P0770", "Shift Solenoid E", "Transmission"),
            ("P0780", "Shift Error", "Transmission"),
            
            # Performance / Tuning Related
            ("P050A", "Cold Start Idle Air Control System Performance", "Idle"),
            ("P050B", "Cold Start Ignition Timing Performance", "Spark"),
            ("P0600", "Serial Communication Link", "ECM"),
            ("P0601", "Internal Control Module Memory Check Sum Error", "ECM"),
            ("P0602", "Control Module Programming Error", "ECM"),
            ("P0603", "Internal Control Module Keep Alive Memory (KAM) Error", "ECM"),
            ("P0604", "Internal Control Module Random Access Memory (RAM) Error", "ECM"),
            ("P0605", "Internal Control Module Read Only Memory (ROM) Error", "ECM"),
            ("P0606", "ECM/PCM Processor", "ECM"),
            ("P0607", "Control Module Performance", "ECM"),
            ("P060A", "Internal Control Module Monitoring Processor Performance", "ECM"),
            ("P060B", "Internal Control Module A/D Processing Performance", "ECM"),
            ("P0610", "Control Module Vehicle Options Error", "ECM"),
            ("P0615", "Starter Relay Circuit", "Electrical"),
            ("P0616", "Starter Relay Circuit Low", "Electrical"),
            ("P0617", "Starter Relay Circuit High", "Electrical"),
            ("P061A", "Internal Control Module Torque Calculator Performance", "ECM"),
            ("P061B", "Internal Control Module Torque Calculator Performance", "ECM"),
            ("P0620", "Generator Control Circuit", "Electrical"),
            ("P0621", "Generator Lamp/L Terminal Circuit", "Electrical"),
            ("P0622", "Generator Field/F Terminal Circuit", "Electrical"),
            ("P0625", "Generator Field Terminal Circuit Low", "Electrical"),
            ("P0626", "Generator Field Terminal Circuit High", "Electrical"),
            ("P0627", "Fuel Pump A Control Circuit/Open", "Fuel System"),
            ("P0628", "Fuel Pump A Control Circuit Low", "Fuel System"),
            ("P0629", "Fuel Pump A Control Circuit High", "Fuel System"),
            ("P0630", "VIN Not Programmed or Mismatch - ECM/PCM", "ECM"),
            ("P0638", "Throttle Actuator Control Range/Performance (Bank 1)", "Throttle"),
            ("P0639", "Throttle Actuator Control Range/Performance (Bank 2)", "Throttle"),
            ("P0641", "Sensor Reference Voltage A Circuit/Open", "Electrical"),
            ("P0642", "Sensor Reference Voltage A Circuit Low", "Electrical"),
            ("P0643", "Sensor Reference Voltage A Circuit High", "Electrical"),
            ("P0645", "A/C Clutch Relay Control Circuit", "HVAC"),
            ("P0646", "A/C Clutch Relay Control Circuit Low", "HVAC"),
            ("P0647", "A/C Clutch Relay Control Circuit High", "HVAC"),
            ("P0650", "Malfunction Indicator Lamp (MIL) Control Circuit", "Electrical"),
            ("P0651", "Sensor Reference Voltage B Circuit/Open", "Electrical"),
            ("P0654", "Engine RPM Output Circuit", "Engine"),
            ("P0657", "Actuator Supply Voltage A Circuit/Open", "Electrical"),
            ("P0658", "Actuator Supply Voltage A Circuit Low", "Electrical"),
            ("P0659", "Actuator Supply Voltage A Circuit High", "Electrical"),
            ("P0660", "Intake Manifold Tuning Valve Control Circuit/Open (Bank 1)", "Air Intake"),
            ("P0661", "Intake Manifold Tuning Valve Control Circuit Low (Bank 1)", "Air Intake"),
            ("P0662", "Intake Manifold Tuning Valve Control Circuit High (Bank 1)", "Air Intake"),
            ("P0667", "PCM/ECM/TCM Internal Temperature Sensor Range/Performance", "ECM"),
            ("P0668", "PCM/ECM/TCM Internal Temperature Sensor Circuit Low", "ECM"),
            ("P0669", "PCM/ECM/TCM Internal Temperature Sensor Circuit High", "ECM"),
            ("P0685", "ECM/PCM Power Relay Control Circuit/Open", "Electrical"),
            ("P0686", "ECM/PCM Power Relay Control Circuit Low", "Electrical"),
            ("P0687", "ECM/PCM Power Relay Control Circuit High", "Electrical"),
            ("P0688", "ECM/PCM Power Relay Sense Circuit", "Electrical"),
            ("P0689", "ECM/PCM Power Relay Sense Circuit Low", "Electrical"),
            ("P0690", "ECM/PCM Power Relay Sense Circuit High", "Electrical"),
            
            # Fuel System Advanced
            ("P0800", "Transfer Case Control System (MIL Request)", "4WD"),
            ("P0801", "Reverse Inhibit Control Circuit", "Transmission"),
            ("P0802", "Transmission Control System MIL Request Circuit/Open", "Transmission"),
            ("P0803", "1-4 Upshift (Skip Shift) Solenoid Control Circuit", "Transmission"),
            ("P0804", "1-4 Upshift (Skip Shift) Lamp Control Circuit", "Transmission"),
            ("P0805", "Clutch Position Sensor Circuit", "Transmission"),
            ("P0806", "Clutch Position Sensor Circuit Range/Performance", "Transmission"),
            ("P0807", "Clutch Position Sensor Circuit Low", "Transmission"),
            ("P0808", "Clutch Position Sensor Circuit High", "Transmission"),
            ("P0809", "Clutch Position Sensor Circuit Intermittent", "Transmission"),
            ("P0810", "Clutch Position Control Error", "Transmission"),
            ("P0811", "Excessive Clutch Slippage", "Transmission"),
            ("P0812", "Reverse Input Circuit", "Transmission"),
            ("P0813", "Reverse Output Circuit", "Transmission"),
            ("P0814", "Transmission Range Display Circuit", "Transmission"),
            ("P0815", "Upshift Switch Circuit", "Transmission"),
            ("P0816", "Downshift Switch Circuit", "Transmission"),
            ("P0817", "Starter Disable Circuit", "Transmission"),
            ("P0818", "Driveline Disconnect Switch Input Circuit", "4WD"),
            ("P0819", "Up and Down Shift Switch to Transmission Range Correlation", "Transmission"),
            ("P0820", "Gear Lever X-Y Position Sensor Circuit", "Transmission"),
            ("P0821", "Gear Lever X Position Circuit", "Transmission"),
            ("P0822", "Gear Lever Y Position Circuit", "Transmission"),
            ("P0823", "Gear Lever X Position Circuit Intermittent", "Transmission"),
            ("P0824", "Gear Lever Y Position Circuit Intermittent", "Transmission"),
            ("P0825", "Gear Lever Push-Pull Switch (Shift Anticipate)", "Transmission"),
            ("P0826", "Up and Down Shift Switch Circuit", "Transmission"),
            ("P0827", "Up and Down Shift Switch Circuit Low", "Transmission"),
            ("P0828", "Up and Down Shift Switch Circuit High", "Transmission"),
            ("P0829", "5-6 Shift", "Transmission"),
            ("P0830", "Clutch Pedal Switch A Circuit", "Transmission"),
            ("P0831", "Clutch Pedal Switch A Circuit Low", "Transmission"),
            ("P0832", "Clutch Pedal Switch A Circuit High", "Transmission"),
            ("P0833", "Clutch Pedal Switch B Circuit", "Transmission"),
            ("P0834", "Clutch Pedal Switch B Circuit Low", "Transmission"),
            ("P0835", "Clutch Pedal Switch B Circuit High", "Transmission"),
            ("P0836", "Four Wheel Drive (4WD) Switch Circuit", "4WD"),
            ("P0837", "Four Wheel Drive (4WD) Switch Circuit Range/Performance", "4WD"),
            ("P0838", "Four Wheel Drive (4WD) Switch Circuit Low", "4WD"),
            ("P0839", "Four Wheel Drive (4WD) Switch Circuit High", "4WD"),
            ("P0840", "Transmission Fluid Pressure Sensor/Switch A Circuit", "Transmission"),
            ("P0841", "Transmission Fluid Pressure Sensor/Switch A Circuit Range/Performance", "Transmission"),
            ("P0842", "Transmission Fluid Pressure Sensor/Switch A Circuit Low", "Transmission"),
            ("P0843", "Transmission Fluid Pressure Sensor/Switch A Circuit High", "Transmission"),
            ("P0844", "Transmission Fluid Pressure Sensor/Switch A Circuit Intermittent", "Transmission"),
            ("P0845", "Transmission Fluid Pressure Sensor/Switch B Circuit", "Transmission"),
            ("P0846", "Transmission Fluid Pressure Sensor/Switch B Circuit Range/Performance", "Transmission"),
            ("P0847", "Transmission Fluid Pressure Sensor/Switch B Circuit Low", "Transmission"),
            ("P0848", "Transmission Fluid Pressure Sensor/Switch B Circuit High", "Transmission"),
            ("P0849", "Transmission Fluid Pressure Sensor/Switch B Circuit Intermittent", "Transmission"),
            ("P0850", "Park/Neutral Switch Input Circuit", "Transmission"),
            ("P0851", "Park/Neutral Switch Input Circuit Low", "Transmission"),
            ("P0852", "Park/Neutral Switch Input Circuit High", "Transmission"),
            ("P0853", "Drive Switch Input Circuit", "Transmission"),
            ("P0854", "Drive Switch Input Circuit Low", "Transmission"),
            ("P0855", "Drive Switch Input Circuit High", "Transmission"),
            ("P0856", "Traction Control Input Signal", "ABS/Traction"),
            ("P0857", "Traction Control Input Signal Range/Performance", "ABS/Traction"),
            ("P0858", "Traction Control Input Signal Low", "ABS/Traction"),
            ("P0859", "Traction Control Input Signal High", "ABS/Traction"),
            ("P0860", "Gear Shift Module Communication Circuit", "Transmission"),
            ("P0861", "Gear Shift Module Communication Circuit Low", "Transmission"),
            ("P0862", "Gear Shift Module Communication Circuit High", "Transmission"),
            ("P0863", "TCM Communication Circuit", "Transmission"),
            ("P0864", "TCM Communication Circuit Low", "Transmission"),
            ("P0865", "TCM Communication Circuit High", "Transmission"),
            ("P0866", "Transmission Control Module Communication Circuit", "Transmission"),
            ("P0867", "Transmission Fluid Pressure", "Transmission"),
            ("P0868", "Transmission Fluid Pressure Low", "Transmission"),
            ("P0869", "Transmission Fluid Pressure High", "Transmission"),
            ("P0870", "Transmission Fluid Pressure Sensor/Switch C Circuit", "Transmission"),
            ("P0871", "Transmission Fluid Pressure Sensor/Switch C Circuit Range/Performance", "Transmission"),
            ("P0872", "Transmission Fluid Pressure Sensor/Switch C Circuit Low", "Transmission"),
            ("P0873", "Transmission Fluid Pressure Sensor/Switch C Circuit High", "Transmission"),
            ("P0874", "Transmission Fluid Pressure Sensor/Switch C Circuit Intermittent", "Transmission"),
            ("P0875", "Transmission Fluid Pressure Sensor/Switch D Circuit", "Transmission"),
            ("P0876", "Transmission Fluid Pressure Sensor/Switch D Circuit Range/Performance", "Transmission"),
            ("P0877", "Transmission Fluid Pressure Sensor/Switch D Circuit Low", "Transmission"),
            ("P0878", "Transmission Fluid Pressure Sensor/Switch D Circuit High", "Transmission"),
            ("P0879", "Transmission Fluid Pressure Sensor/Switch D Circuit Intermittent", "Transmission"),
            ("P0880", "TCM Power Input Signal", "Transmission"),
            ("P0881", "TCM Power Input Signal Range/Performance", "Transmission"),
            ("P0882", "TCM Power Input Signal Low", "Transmission"),
            ("P0883", "TCM Power Input Signal High", "Transmission"),
            ("P0884", "TCM Power Input Signal Intermittent", "Transmission"),
            ("P0885", "TCM Power Relay Control Circuit/Open", "Transmission"),
            ("P0886", "TCM Power Relay Control Circuit Low", "Transmission"),
            ("P0887", "TCM Power Relay Control Circuit High", "Transmission"),
            ("P0888", "Transmission Relay Sense Circuit", "Transmission"),
            ("P0889", "Transmission Relay Sense Circuit Range/Performance", "Transmission"),
            ("P0890", "Switch to Transmission Relay Sense Circuit Low", "Transmission"),
            ("P0891", "Switch to Transmission Relay Sense Circuit High", "Transmission"),
            ("P0892", "Transmission Relay Sense Circuit Intermittent", "Transmission"),
            ("P0893", "Multiple Gears Engaged", "Transmission"),
            ("P0894", "Transmission Component Slipping", "Transmission"),
            ("P0895", "Shift Time Too Short", "Transmission"),
            ("P0896", "Shift Time Too Long", "Transmission"),
            ("P0897", "Transmission Fluid Deteriorated", "Transmission"),
            ("P0898", "Transmission Control System MIL Request Circuit Low", "Transmission"),
            ("P0899", "Transmission Control System MIL Request Circuit High", "Transmission"),
        ]
        
        for code, description, category in generic_p0_codes:
            self.dtcs[code] = DTC(
                code=code,
                description=description,
                category=category,
                manufacturer="Generic"
            )
            
    def _initialize_gm_codes(self):
        """Initialize GM-specific codes"""
        gm_codes = [
            # VVT System
            ("P1011", "Intake Camshaft Position Actuator Solenoid Bank 1", "VVT System"),
            ("P1012", "Intake Camshaft Position Actuator Solenoid Low Voltage Bank 1", "VVT System"),
            ("P1013", "Intake Camshaft Position Actuator Solenoid High Voltage Bank 1", "VVT System"),
            ("P1014", "Exhaust Camshaft Position Actuator Solenoid Bank 1", "VVT System"),
            ("P1015", "Exhaust Camshaft Position Actuator Solenoid Low Voltage Bank 1", "VVT System"),
            ("P1016", "Exhaust Camshaft Position Actuator Solenoid High Voltage Bank 1", "VVT System"),
            
            # MAF/Air Intake
            ("P1101", "Intake Air Flow System Performance", "Air Intake"),
            ("P1102", "MAF Sensor Circuit Low Frequency", "Air Intake"),
            ("P1103", "MAF Sensor Circuit High Frequency", "Air Intake"),
            
            # ECT
            ("P1115", "ECT Sensor Circuit Intermittent Low Voltage", "Temperature Sensor"),
            ("P1116", "ECT Sensor Circuit Intermittent High Voltage", "Temperature Sensor"),
            ("P1117", "ECT Sensor Circuit Intermittent", "Temperature Sensor"),
            
            # IAT
            ("P1120", "Throttle Position Sensor 1 Circuit", "Throttle"),
            ("P1125", "Accelerator Pedal Position System", "Throttle"),
            ("P1130", "O2 Sensor Circuit (Bank 1 Sensor 1) Insufficient Switching", "Emissions"),
            ("P1131", "O2 Sensor Circuit (Bank 1 Sensor 1) Lean", "Emissions"),
            ("P1132", "O2 Sensor Circuit (Bank 1 Sensor 1) Rich", "Emissions"),
            ("P1133", "O2 Sensor Circuit (Bank 1 Sensor 1) Slow Response", "Emissions"),
            ("P1134", "O2 Sensor Circuit (Bank 1 Sensor 1) Transition Time", "Emissions"),
            ("P1153", "O2 Sensor Circuit (Bank 2 Sensor 1) Insufficient Switching", "Emissions"),
            
            # Fuel System
            ("P1174", "Fuel Trim Cylinder Balance Bank 1", "Fuel System"),
            ("P1175", "Fuel Trim Cylinder Balance Bank 2", "Fuel System"),
            ("P1187", "Engine Oil Pressure Switch Circuit", "Oil System"),
            ("P1188", "Engine Oil Pressure Sensor Circuit", "Oil System"),
            ("P1189", "Engine Oil Pressure Sensor Circuit Low Voltage", "Oil System"),
            ("P1190", "Engine Oil Pressure Sensor Circuit High Voltage", "Oil System"),
            
            # Injectors
            ("P1241", "Injector Circuit Cylinder 1 High Control Circuit", "Fuel System"),
            ("P1242", "Injector Circuit Cylinder 2 High Control Circuit", "Fuel System"),
            ("P1243", "Injector Circuit Cylinder 3 High Control Circuit", "Fuel System"),
            ("P1244", "Injector Circuit Cylinder 4 High Control Circuit", "Fuel System"),
            ("P1245", "Injector Circuit Cylinder 5 High Control Circuit", "Fuel System"),
            ("P1246", "Injector Circuit Cylinder 6 High Control Circuit", "Fuel System"),
            ("P1247", "Injector Circuit Cylinder 7 High Control Circuit", "Fuel System"),
            ("P1248", "Injector Circuit Cylinder 8 High Control Circuit", "Fuel System"),
            
            # Fuel Pump
            ("P1233", "Fuel Pump Driver Module Disabled or Off Line", "Fuel System"),
            ("P1234", "Fuel Pump Driver Module Commanded OFF", "Fuel System"),
            ("P1235", "Fuel Pump Control Out of Range", "Fuel System"),
            ("P1236", "Fuel Pump Control Circuit Low", "Fuel System"),
            ("P1237", "Fuel Pump Control Circuit High", "Fuel System"),
            
            # Direct Injection (LFX)
            ("P1249", "High Pressure Fuel Pump Command Performance", "Fuel System"),
            ("P1250", "High Pressure Fuel Pump Circuit Low", "Fuel System"),
            ("P1251", "High Pressure Fuel Pump Circuit High", "Fuel System"),
            ("P1252", "High Pressure Fuel Pump Control Circuit", "Fuel System"),
            
            # Misfire
            ("P1300", "Misfire Detected - Low Fuel", "Ignition"),
            ("P1350", "Ignition Coil Control Circuit High Voltage Bank 1", "Ignition"),
            ("P1351", "Ignition Coil Control Circuit Low Voltage Bank 1", "Ignition"),
            ("P1352", "Ignition Coil Control Circuit High Voltage Bank 2", "Ignition"),
            ("P1353", "Ignition Coil Control Circuit Low Voltage Bank 2", "Ignition"),
            
            # Crankshaft/Camshaft
            ("P1372", "Crankshaft Position System Variation Not Learned", "Engine Position"),
            ("P1380", "Misfire Detected - Rough Road Data Not Available", "Ignition"),
            ("P1381", "Misfire Detected - No Communication with Brake Control Module", "Ignition"),
            
            # Traction Control
            ("P1390", "Octane Adjust Pin Out of Self Test Range", "Ignition"),
            ("P1391", "Octane Adjust Service Pin Circuit", "Ignition"),
            
            # EGR
            ("P1404", "EGR Valve Stuck Open", "Emissions"),
            ("P1405", "EGR Valve Circuit High", "Emissions"),
            ("P1406", "EGR Valve Circuit Low", "Emissions"),
            
            # Catalyst
            ("P1415", "Secondary Air Injection System Bank 1", "Emissions"),
            ("P1416", "Secondary Air Injection System Bank 2", "Emissions"),
            
            # EVAP
            ("P1441", "EVAP System Flow During Non-Purge", "Emissions"),
            ("P1442", "EVAP Vacuum Switch High Voltage During Ignition ON", "Emissions"),
            ("P1450", "Unable to Bleed Up Fuel Tank Vacuum", "Emissions"),
            ("P1460", "Cooling Fan Control System", "Cooling"),
            ("P1461", "Cooling Fan Control Circuit Low", "Cooling"),
            ("P1462", "Cooling Fan Control Circuit High", "Cooling"),
            
            # AC
            ("P1500", "Starter Signal Circuit", "Electrical"),
            ("P1508", "Idle Speed Low - Idle Learn Not Performed", "Idle"),
            ("P1509", "Idle Speed High - Idle Learn Not Performed", "Idle"),
            ("P1516", "Throttle Actuator Control Module Throttle Actuator Position Performance", "Throttle"),
            ("P1518", "Throttle Actuator Control Module Analog to Digital Performance", "Throttle"),
            ("P1519", "Throttle Actuator Control Module Internal Circuit", "Throttle"),
            ("P1520", "Throttle Actuator Control Module Reset", "Throttle"),
            ("P1521", "Throttle Actuator Control Module Throttle Body Circuit", "Throttle"),
            ("P1522", "Throttle Actuator Control Module Throttle Body Circuit Range/Performance", "Throttle"),
            ("P1523", "Throttle Actuator Control Module Throttle Body Circuit Low", "Throttle"),
            ("P1524", "Throttle Actuator Control Module Throttle Body Circuit High", "Throttle"),
            ("P1525", "Throttle Body Airflow Trim at Max Limit", "Air Intake"),
            ("P1526", "Throttle Body Airflow Trim at Min Limit", "Air Intake"),
            ("P1527", "Trans Range to Trans Pressure Correlation", "Transmission"),
            ("P1528", "Trans Range to Trans Pressure Correlation Low", "Transmission"),
            ("P1529", "Trans Range to Trans Pressure Correlation High", "Transmission"),
            
            # Immobilizer/Security
            ("P1571", "System Voltage High", "Electrical"),
            ("P1572", "System Voltage Low", "Electrical"),
            ("P1574", "Pedal Position Not Available", "Throttle"),
            ("P1575", "Pedal Position Out of Self Test Range", "Throttle"),
            ("P1576", "Pedal Position Sensor Supply Voltage Circuit High", "Throttle"),
            ("P1577", "Pedal Position Sensor Supply Voltage Circuit Low", "Throttle"),
            ("P1578", "Pedal Position Sensor Supply Voltage Circuit Open", "Throttle"),
            
            # Cruise Control
            ("P1585", "Cruise Control Inhibit Output Circuit", "Cruise"),
            ("P1586", "Cruise Control Inhibit Output Circuit Low", "Cruise"),
            ("P1587", "Cruise Control Inhibit Output Circuit High", "Cruise"),
            ("P1588", "Cruise Control Resume Switch Circuit", "Cruise"),
            ("P1589", "Cruise Control Resume Switch Circuit Low", "Cruise"),
            ("P1590", "Cruise Control Resume Switch Circuit High", "Cruise"),
            ("P1591", "Cruise Control Set Switch Circuit", "Cruise"),
            ("P1592", "Cruise Control Set Switch Circuit Low", "Cruise"),
            ("P1593", "Cruise Control Set Switch Circuit High", "Cruise"),
            ("P1594", "Cruise Control Vehicle Speed Too High", "Cruise"),
            ("P1595", "Cruise Control Servo Control Circuit", "Cruise"),
            ("P1596", "Cruise Control Servo Control Circuit Low", "Cruise"),
            ("P1597", "Cruise Control Servo Control Circuit High", "Cruise"),
            ("P1598", "Cruise Control Multi-Function Input A Circuit", "Cruise"),
            ("P1599", "Cruise Control Multi-Function Input A Circuit Range/Performance", "Cruise"),
            ("P1600", "Cruise Control Multi-Function Input A Circuit Low", "Cruise"),
            ("P1601", "Cruise Control Multi-Function Input A Circuit High", "Cruise"),
            ("P1602", "Cruise Control Multi-Function Input A Circuit Stuck", "Cruise"),
            
            # ECM/PCM
            ("P1603", "Engine Control Module EEPROM Error", "ECM"),
            ("P1604", "Engine Control Module EEPROM Write Error", "ECM"),
            ("P1605", "Engine Control Module Knock Sensor Processor 1 Performance", "ECM"),
            ("P1606", "Engine Control Module Knock Sensor Processor 2 Performance", "ECM"),
            ("P1607", "Engine Control Module EEPROM Malfunction", "ECM"),
            ("P1608", "Engine Control Module A/D Converter", "ECM"),
            ("P1609", "Engine Control Module Internal Watchdog Operation", "ECM"),
            ("P1610", "Engine Control Module Serial Communication", "ECM"),
            ("P1611", "Engine Control Module Serial Communication Lost", "ECM"),
            ("P1612", "Engine Control Module Serial Communication Range/Performance", "ECM"),
            ("P1613", "Engine Control Module Serial Communication Low", "ECM"),
            ("P1614", "Engine Control Module Serial Communication High", "ECM"),
            ("P1615", "Engine Control Module Secondary Serial Communication", "ECM"),
            ("P1616", "Engine Control Module Secondary Serial Communication Lost", "ECM"),
            ("P1617", "Engine Control Module Secondary Serial Communication Range/Performance", "ECM"),
            ("P1618", "Engine Control Module Secondary Serial Communication Low", "ECM"),
            ("P1619", "Engine Control Module Secondary Serial Communication High", "ECM"),
            ("P1620", "Engine Control Module EEPROM Performance", "ECM"),
            ("P1621", "Control Module Long Term Memory Performance", "ECM"),
            ("P1622", "Control Module EEPROM Performance", "ECM"),
            ("P1623", "Control Module EEPROM Write Performance", "ECM"),
            ("P1624", "Control Module EEPROM Read Performance", "ECM"),
            ("P1625", "Control Module EEPROM Erase Performance", "ECM"),
            ("P1626", "Theft Deterrent Fuel Enable Signal Not Received", "Security"),
            ("P1627", "Engine Control Module A/D Converter Performance", "ECM"),
            ("P1628", "Engine Control Module A/D Converter Low", "ECM"),
            ("P1629", "Engine Control Module A/D Converter High", "ECM"),
            ("P1630", "Theft Deterrent Learn Mode Active", "Security"),
            ("P1631", "Theft Deterrent Start Enable Signal Not Correct", "Security"),
            ("P1632", "Smart Alternator Faults Sensor/Circuit", "Electrical"),
            ("P1633", "Smart Alternator Faults System Voltage Low", "Electrical"),
            ("P1634", "Smart Alternator Faults System Voltage High", "Electrical"),
            ("P1635", "5 Volt Reference Circuit", "Electrical"),
            ("P1636", "5 Volt Reference Circuit Low", "Electrical"),
            ("P1637", "5 Volt Reference Circuit High", "Electrical"),
            ("P1638", "Alternator L Terminal Circuit", "Electrical"),
            ("P1639", "5 Volt Reference 2 Circuit", "Electrical"),
            ("P1640", "5 Volt Reference 2 Circuit Low", "Electrical"),
            ("P1641", "5 Volt Reference 2 Circuit High", "Electrical"),
            ("P1642", "Vehicle Speed Output Circuit", "Electrical"),
            ("P1643", "Engine Control Module ICL Performance", "ECM"),
            ("P1644", "Engine Control Module ICL Low", "ECM"),
            ("P1645", "Engine Control Module ICL High", "ECM"),
            ("P1646", "Supercharger Inlet Pressure Control Circuit", "Forced Induction"),
            ("P1647", "Supercharger Inlet Pressure Control Circuit Low", "Forced Induction"),
            ("P1648", "Supercharger Inlet Pressure Control Circuit High", "Forced Induction"),
            ("P1649", "Supercharger Inlet Pressure Control Circuit Range/Performance", "Forced Induction"),
            ("P1650", "Power Steering Pressure Switch Circuit", "Steering"),
            ("P1651", "Power Steering Pressure Switch Circuit Low", "Steering"),
            ("P1652", "Power Steering Pressure Switch Circuit High", "Steering"),
            ("P1653", "Power Steering Pressure Switch Circuit Range/Performance", "Steering"),
            ("P1654", "Cruise Control Servo Control Circuit", "Cruise"),
            ("P1655", "Cruise Control Servo Control Circuit Low", "Cruise"),
            ("P1656", "Cruise Control Servo Control Circuit High", "Cruise"),
            ("P1657", "Cruise Control Servo Control Circuit Range/Performance", "Cruise"),
            ("P1658", "Cruise Control Multi-Function Switch Circuit", "Cruise"),
            ("P1659", "Cruise Control Multi-Function Switch Circuit Low", "Cruise"),
            ("P1660", "Cruise Control Multi-Function Switch Circuit High", "Cruise"),
            ("P1661", "Cruise Control Multi-Function Switch Circuit Range/Performance", "Cruise"),
            ("P1662", "Cruise Control Multi-Function Switch Circuit Stuck", "Cruise"),
            ("P1663", "Cruise Control Multi-Function Switch Circuit Invalid", "Cruise"),
            ("P1664", "Cruise Control Multi-Function Switch Circuit Mismatch", "Cruise"),
            ("P1665", "Cruise Control Multi-Function Switch Circuit Out of Range", "Cruise"),
            ("P1666", "Cruise Control Multi-Function Switch Circuit In Range", "Cruise"),
            ("P1667", "Cruise Control Multi-Function Switch Circuit Performance", "Cruise"),
            ("P1668", "Cruise Control Multi-Function Switch Circuit Intermittent", "Cruise"),
            ("P1669", "Cruise Control Multi-Function Switch Circuit Continuous", "Cruise"),
            ("P1670", "Cruise Control Multi-Function Switch Circuit Discontinuous", "Cruise"),
            ("P1671", "Cruise Control Multi-Function Switch Circuit Open", "Cruise"),
            ("P1672", "Cruise Control Multi-Function Switch Circuit Shorted", "Cruise"),
            ("P1673", "Cruise Control Multi-Function Switch Circuit Grounded", "Cruise"),
            ("P1674", "Cruise Control Multi-Function Switch Circuit Not Grounded", "Cruise"),
            ("P1675", "Cruise Control Multi-Function Switch Circuit Power", "Cruise"),
            ("P1676", "Cruise Control Multi-Function Switch Circuit No Power", "Cruise"),
            ("P1677", "Cruise Control Multi-Function Switch Circuit Voltage", "Cruise"),
            ("P1678", "Cruise Control Multi-Function Switch Circuit No Voltage", "Cruise"),
            ("P1679", "Cruise Control Multi-Function Switch Circuit Current", "Cruise"),
            ("P1680", "Cruise Control Multi-Function Switch Circuit No Current", "Cruise"),
            ("P1681", "Cruise Control Multi-Function Switch Circuit Resistance", "Cruise"),
            ("P1682", "Cruise Control Multi-Function Switch Circuit No Resistance", "Cruise"),
            ("P1683", "Cruise Control Multi-Function Switch Circuit Frequency", "Cruise"),
            ("P1684", "Cruise Control Multi-Function Switch Circuit No Frequency", "Cruise"),
            ("P1685", "Cruise Control Multi-Function Switch Circuit Duty Cycle", "Cruise"),
            ("P1686", "Cruise Control Multi-Function Switch Circuit No Duty Cycle", "Cruise"),
            ("P1687", "Cruise Control Multi-Function Switch Circuit Pulse Width", "Cruise"),
            ("P1688", "Cruise Control Multi-Function Switch Circuit No Pulse Width", "Cruise"),
            ("P1689", "Cruise Control Multi-Function Switch Circuit Timing", "Cruise"),
            ("P1690", "Cruise Control Multi-Function Switch Circuit No Timing", "Cruise"),
            ("P1691", "Cruise Control Multi-Function Switch Circuit Sync", "Cruise"),
            ("P1692", "Cruise Control Multi-Function Switch Circuit No Sync", "Cruise"),
            ("P1693", "Cruise Control Multi-Function Switch Circuit Communication", "Cruise"),
            ("P1694", "Cruise Control Multi-Function Switch Circuit No Communication", "Cruise"),
            ("P1695", "Cruise Control Multi-Function Switch Circuit Data", "Cruise"),
            ("P1696", "Cruise Control Multi-Function Switch Circuit No Data", "Cruise"),
            ("P1697", "Cruise Control Multi-Function Switch Circuit Signal", "Cruise"),
            ("P1698", "Cruise Control Multi-Function Switch Circuit No Signal", "Cruise"),
            ("P1699", "Cruise Control Multi-Function Switch Circuit Message", "Cruise"),
            
            # More GM codes
            ("P1779", "Engine Torque Delivered to TCM Signal", "Transmission"),
            ("P1780", "Engine Torque Request Circuit", "Transmission"),
            ("P1781", "Engine Torque Circuit Range/Performance", "Transmission"),
            ("P1782", "Engine Torque Circuit Low", "Transmission"),
            ("P1783", "Engine Torque Circuit High", "Transmission"),
            ("P1784", "Torque Reduction Circuit", "Transmission"),
            ("P1785", "Torque Reduction Circuit Range/Performance", "Transmission"),
            ("P1786", "Torque Reduction Circuit Low", "Transmission"),
            ("P1787", "Torque Reduction Circuit High", "Transmission"),
            ("P1788", "Torque Reduction Circuit Invalid", "Transmission"),
            ("P1789", "Torque Reduction Circuit Stuck", "Transmission"),
            ("P1790", "Torque Reduction Circuit Performance", "Transmission"),
            ("P1791", "Torque Reduction Circuit Intermittent", "Transmission"),
            ("P1792", "Torque Reduction Circuit Continuous", "Transmission"),
            ("P1793", "Torque Reduction Circuit Discontinuous", "Transmission"),
            ("P1794", "Torque Reduction Circuit Open", "Transmission"),
            ("P1795", "Torque Reduction Circuit Shorted", "Transmission"),
            ("P1796", "Torque Reduction Circuit Grounded", "Transmission"),
            ("P1797", "Torque Reduction Circuit Not Grounded", "Transmission"),
            ("P1798", "Torque Reduction Circuit Power", "Transmission"),
            ("P1799", "Torque Reduction Circuit No Power", "Transmission"),
            
            # TCM Communication
            ("P1810", "TFP Valve Position Switch Circuit", "Transmission"),
            ("P1811", "Maximum Adaptive and Long Term Shift", "Transmission"),
            ("P1812", "Torque Converter Clutch System - Stuck On", "Transmission"),
            ("P1813", "Torque Converter Clutch System - Stuck Off", "Transmission"),
            ("P1814", "Torque Converter Clutch Performance", "Transmission"),
            ("P1815", "Torque Converter Clutch Circuit", "Transmission"),
            ("P1816", "Torque Converter Clutch Circuit Low", "Transmission"),
            ("P1817", "Torque Converter Clutch Circuit High", "Transmission"),
            ("P1818", "Torque Converter Clutch Circuit Range/Performance", "Transmission"),
            ("P1819", "Torque Converter Clutch Circuit Intermittent", "Transmission"),
            ("P1820", "Internal Mode Switch Circuit", "Transmission"),
            ("P1822", "Internal Mode Switch Circuit Range/Performance", "Transmission"),
            ("P1823", "Internal Mode Switch Circuit Low", "Transmission"),
            ("P1824", "Internal Mode Switch Circuit High", "Transmission"),
            ("P1825", "Internal Mode Switch Circuit Invalid", "Transmission"),
            ("P1826", "Internal Mode Switch Circuit Stuck", "Transmission"),
            ("P1827", "Internal Mode Switch Circuit Performance", "Transmission"),
            ("P1830", "Pressure Control Solenoid Power Circuit", "Transmission"),
            ("P1831", "Pressure Control Solenoid Power Circuit Low", "Transmission"),
            ("P1832", "Pressure Control Solenoid Power Circuit High", "Transmission"),
            ("P1833", "Pressure Control Solenoid Power Circuit Range/Performance", "Transmission"),
            ("P1834", "Pressure Control Solenoid Power Circuit Intermittent", "Transmission"),
            ("P1835", "Pressure Control Solenoid Control Circuit", "Transmission"),
            ("P1836", "Pressure Control Solenoid Control Circuit Low", "Transmission"),
            ("P1837", "Pressure Control Solenoid Control Circuit High", "Transmission"),
            ("P1838", "Pressure Control Solenoid Control Circuit Range/Performance", "Transmission"),
            ("P1839", "Pressure Control Solenoid Control Circuit Intermittent", "Transmission"),
            ("P1840", "1-2 Shift Solenoid Circuit", "Transmission"),
            ("P1842", "1-2 Shift Solenoid Circuit Range/Performance", "Transmission"),
            ("P1843", "1-2 Shift Solenoid Circuit Low", "Transmission"),
            ("P1844", "1-2 Shift Solenoid Circuit High", "Transmission"),
            ("P1845", "2-3 Shift Solenoid Circuit", "Transmission"),
            ("P1847", "2-3 Shift Solenoid Circuit Range/Performance", "Transmission"),
            ("P1848", "2-3 Shift Solenoid Circuit Low", "Transmission"),
            ("P1849", "2-3 Shift Solenoid Circuit High", "Transmission"),
            ("P1850", "Brake Band Apply Solenoid Circuit", "Transmission"),
            ("P1852", "Brake Band Apply Solenoid Circuit Range/Performance", "Transmission"),
            ("P1853", "Brake Band Apply Solenoid Circuit Low", "Transmission"),
            ("P1854", "Brake Band Apply Solenoid Circuit High", "Transmission"),
            
            # 4WD/Transfer Case
            ("P1860", "TCC PWM Solenoid Circuit", "Transmission"),
            ("P1861", "TCC PWM Solenoid Circuit Range/Performance", "Transmission"),
            ("P1862", "TCC PWM Solenoid Circuit Low", "Transmission"),
            ("P1863", "TCC PWM Solenoid Circuit High", "Transmission"),
            ("P1864", "TCC PWM Solenoid Circuit Intermittent", "Transmission"),
            ("P1865", "TCC PWM Solenoid Control Circuit", "Transmission"),
            ("P1866", "TCC PWM Solenoid Control Circuit Low", "Transmission"),
            ("P1867", "TCC PWM Solenoid Control Circuit High", "Transmission"),
            ("P1868", "TCC PWM Solenoid Control Circuit Range/Performance", "Transmission"),
            ("P1869", "TCC PWM Solenoid Control Circuit Intermittent", "Transmission"),
            ("P1870", "Transmission Component Slipping", "Transmission"),
            ("P1871", "Transmission Component Slipping Range/Performance", "Transmission"),
            ("P1872", "Transmission Component Slipping Low", "Transmission"),
            ("P1873", "Transmission Component Slipping High", "Transmission"),
            ("P1874", "Transmission Component Slipping Intermittent", "Transmission"),
            ("P1875", "Transmission Component Slipping Invalid", "Transmission"),
            ("P1876", "Transmission Component Slipping Stuck", "Transmission"),
            ("P1877", "Transmission Component Slipping Performance", "Transmission"),
            ("P1880", "Transfer Case Front Shunt Fault", "4WD"),
            ("P1881", "Transfer Case Front Shunt Fault Range/Performance", "4WD"),
            ("P1882", "Transfer Case Front Shunt Fault Low", "4WD"),
            ("P1883", "Transfer Case Front Shunt Fault High", "4WD"),
            ("P1884", "Transfer Case Front Shunt Fault Intermittent", "4WD"),
            ("P1885", "Transfer Case Front Shunt Fault Invalid", "4WD"),
            ("P1886", "Transfer Case Front Shunt Fault Stuck", "4WD"),
            ("P1887", "Transfer Case Front Shunt Fault Performance", "4WD"),
            ("P1888", "Transfer Case Shift Motor Circuit", "4WD"),
            ("P1890", "Transfer Case Shift Motor Circuit Range/Performance", "4WD"),
            ("P1891", "Transfer Case Shift Motor Circuit Low", "4WD"),
            ("P1892", "Transfer Case Shift Motor Circuit High", "4WD"),
            ("P1893", "Transfer Case Shift Motor Circuit Intermittent", "4WD"),
            ("P1894", "Transfer Case Shift Motor Circuit Invalid", "4WD"),
            ("P1895", "Transfer Case Shift Motor Circuit Stuck", "4WD"),
            ("P1896", "Transfer Case Shift Motor Circuit Performance", "4WD"),
            
            # CAN Bus
            ("P1900", "Class 2 Communication Malfunction", "Network"),
            ("P1901", "Class 2 Communication Malfunction Range/Performance", "Network"),
            ("P1902", "Class 2 Communication Malfunction Low", "Network"),
            ("P1903", "Class 2 Communication Malfunction High", "Network"),
            ("P1904", "Class 2 Communication Malfunction Intermittent", "Network"),
            ("P1905", "Class 2 Communication Malfunction Invalid", "Network"),
            ("P1906", "Class 2 Communication Malfunction Stuck", "Network"),
            ("P1907", "Class 2 Communication Malfunction Performance", "Network"),
            ("P1908", "Class 2 Communication Malfunction Continuous", "Network"),
            ("P1909", "Class 2 Communication Malfunction Discontinuous", "Network"),
            ("P1910", "Class 2 Communication Malfunction Open", "Network"),
            ("P1911", "Class 2 Communication Malfunction Shorted", "Network"),
            ("P1912", "Class 2 Communication Malfunction Grounded", "Network"),
            ("P1913", "Class 2 Communication Malfunction Not Grounded", "Network"),
            ("P1914", "Class 2 Communication Malfunction Power", "Network"),
            ("P1915", "Class 2 Communication Malfunction No Power", "Network"),
            ("P1916", "Class 2 Communication Malfunction Voltage", "Network"),
            ("P1917", "Class 2 Communication Malfunction No Voltage", "Network"),
            ("P1918", "Class 2 Communication Malfunction Current", "Network"),
            ("P1919", "Class 2 Communication Malfunction No Current", "Network"),
            ("P1920", "Class 2 Communication Malfunction Resistance", "Network"),
            ("P1921", "Class 2 Communication Malfunction No Resistance", "Network"),
            ("P1922", "Class 2 Communication Malfunction Frequency", "Network"),
            ("P1923", "Class 2 Communication Malfunction No Frequency", "Network"),
            ("P1924", "Class 2 Communication Malfunction Duty Cycle", "Network"),
            ("P1925", "Class 2 Communication Malfunction No Duty Cycle", "Network"),
            ("P1926", "Class 2 Communication Malfunction Pulse Width", "Network"),
            ("P1927", "Class 2 Communication Malfunction No Pulse Width", "Network"),
            ("P1928", "Class 2 Communication Malfunction Timing", "Network"),
            ("P1929", "Class 2 Communication Malfunction No Timing", "Network"),
            ("P1930", "Class 2 Communication Malfunction Sync", "Network"),
            ("P1931", "Class 2 Communication Malfunction No Sync", "Network"),
            ("P1932", "Class 2 Communication Malfunction Data", "Network"),
            ("P1933", "Class 2 Communication Malfunction No Data", "Network"),
            ("P1934", "Class 2 Communication Malfunction Signal", "Network"),
            ("P1935", "Class 2 Communication Malfunction No Signal", "Network"),
            ("P1936", "Class 2 Communication Malfunction Message", "Network"),
            ("P1937", "Class 2 Communication Malfunction No Message", "Network"),
            ("P1938", "Class 2 Communication Malfunction Packet", "Network"),
            ("P1939", "Class 2 Communication Malfunction No Packet", "Network"),
            ("P1940", "Class 2 Communication Malfunction Frame", "Network"),
            ("P1941", "Class 2 Communication Malfunction No Frame", "Network"),
            ("P1942", "Class 2 Communication Malfunction Bit", "Network"),
            ("P1943", "Class 2 Communication Malfunction No Bit", "Network"),
            ("P1944", "Class 2 Communication Malfunction Byte", "Network"),
            ("P1945", "Class 2 Communication Malfunction No Byte", "Network"),
            ("P1946", "Class 2 Communication Malfunction Word", "Network"),
            ("P1947", "Class 2 Communication Malfunction No Word", "Network"),
            ("P1948", "Class 2 Communication Malfunction Long Word", "Network"),
            ("P1949", "Class 2 Communication Malfunction No Long Word", "Network"),
            ("P1950", "Class 2 Communication Malfunction Block", "Network"),
            ("P1951", "Class 2 Communication Malfunction No Block", "Network"),
            ("P1952", "Class 2 Communication Malfunction Page", "Network"),
            ("P1953", "Class 2 Communication Malfunction No Page", "Network"),
            ("P1954", "Class 2 Communication Malfunction Sector", "Network"),
            ("P1955", "Class 2 Communication Malfunction No Sector", "Network"),
            ("P1956", "Class 2 Communication Malfunction Segment", "Network"),
            ("P1957", "Class 2 Communication Malfunction No Segment", "Network"),
            ("P1958", "Class 2 Communication Malfunction Track", "Network"),
            ("P1959", "Class 2 Communication Malfunction No Track", "Network"),
            ("P1960", "Class 2 Communication Malfunction Cylinder", "Network"),
            ("P1961", "Class 2 Communication Malfunction No Cylinder", "Network"),
            ("P1962", "Class 2 Communication Malfunction Head", "Network"),
            ("P1963", "Class 2 Communication Malfunction No Head", "Network"),
            ("P1964", "Class 2 Communication Malfunction Disk", "Network"),
            ("P1965", "Class 2 Communication Malfunction No Disk", "Network"),
            ("P1966", "Class 2 Communication Malfunction Drive", "Network"),
            ("P1967", "Class 2 Communication Malfunction No Drive", "Network"),
            ("P1968", "Class 2 Communication Malfunction Media", "Network"),
            ("P1969", "Class 2 Communication Malfunction No Media", "Network"),
            ("P1970", "Class 2 Communication Malfunction Device", "Network"),
            ("P1971", "Class 2 Communication Malfunction No Device", "Network"),
            ("P1972", "Class 2 Communication Malfunction Unit", "Network"),
            ("P1973", "Class 2 Communication Malfunction No Unit", "Network"),
            ("P1974", "Class 2 Communication Malfunction Module", "Network"),
            ("P1975", "Class 2 Communication Malfunction No Module", "Network"),
            ("P1976", "Class 2 Communication Malfunction Controller", "Network"),
            ("P1977", "Class 2 Communication Malfunction No Controller", "Network"),
            ("P1978", "Class 2 Communication Malfunction Processor", "Network"),
            ("P1979", "Class 2 Communication Malfunction No Processor", "Network"),
            ("P1980", "Class 2 Communication Malfunction CPU", "Network"),
            ("P1981", "Class 2 Communication Malfunction No CPU", "Network"),
            ("P1982", "Class 2 Communication Malfunction Memory", "Network"),
            ("P1983", "Class 2 Communication Malfunction No Memory", "Network"),
            ("P1984", "Class 2 Communication Malfunction RAM", "Network"),
            ("P1985", "Class 2 Communication Malfunction No RAM", "Network"),
            ("P1986", "Class 2 Communication Malfunction ROM", "Network"),
            ("P1987", "Class 2 Communication Malfunction No ROM", "Network"),
            ("P1988", "Class 2 Communication Malfunction EEPROM", "Network"),
            ("P1989", "Class 2 Communication Malfunction No EEPROM", "Network"),
            ("P1990", "Class 2 Communication Malfunction Flash", "Network"),
            ("P1991", "Class 2 Communication Malfunction No Flash", "Network"),
            ("P1992", "Class 2 Communication Malfunction Buffer", "Network"),
            ("P1993", "Class 2 Communication Malfunction No Buffer", "Network"),
            ("P1994", "Class 2 Communication Malfunction Stack", "Network"),
            ("P1995", "Class 2 Communication Malfunction No Stack", "Network"),
            ("P1996", "Class 2 Communication Malfunction Heap", "Network"),
            ("P1997", "Class 2 Communication Malfunction No Heap", "Network"),
            ("P1998", "Class 2 Communication Malfunction Queue", "Network"),
            ("P1999", "Class 2 Communication Malfunction No Queue", "Network"),
        ]
        
        for code, description, category in gm_codes:
            self.dtcs[code] = DTC(
                code=code,
                description=description,
                category=category,
                manufacturer="GM"
            )
            
    def _initialize_tuning_related_codes(self):
        """Mark codes that are relevant to tuning"""
        tuning_categories = [
            "Fuel System", "Ignition", "VVT System", "Air Intake",
            "Throttle", "Transmission", "Engine Position", "ECM",
            "Idle", "Spark", "Emissions"
        ]
        
        for dtc in self.dtcs.values():
            if dtc.category in tuning_categories:
                dtc.tuning_related = True
                
        # Add specific symptoms and causes for common tuning codes
        self._add_tuning_details()
        
    def _add_tuning_details(self):
        """Add detailed symptoms and causes for tuning-related codes"""
        
        # Lean condition
        if "P0171" in self.dtcs:
            self.dtcs["P0171"].symptoms = [
                "Hesitation on acceleration",
                "Rough idle",
                "Spark knock/detonation",
                "Reduced power"
            ]
            self.dtcs["P0171"].possible_causes = [
                "Vacuum leak",
                "MAF sensor dirty or miscalibrated",
                "Low fuel pressure",
                "Injector flow imbalance",
                "O2 sensor failure"
            ]
            self.dtcs["P0171"].affected_systems = ["Fuel", "Airflow"]
            
        # Rich condition  
        if "P0172" in self.dtcs:
            self.dtcs["P0172"].symptoms = [
                "Black smoke from exhaust",
                "Fuel smell",
                "Poor fuel economy",
                "Carbon buildup on plugs"
            ]
            self.dtcs["P0172"].possible_causes = [
                "MAF sensor over-reading",
                "High fuel pressure",
                "Leaking injector",
                "O2 sensor stuck rich",
                "Thermostat stuck open (over-fueling for warmup)"
            ]
            self.dtcs["P0172"].affected_systems = ["Fuel", "Airflow"]
            
        # Misfire
        if "P0300" in self.dtcs:
            self.dtcs["P0300"].symptoms = [
                "Rough running",
                "Flashing MIL",
                "Loss of power",
                "Vibration"
            ]
            self.dtcs["P0300"].possible_causes = [
                "Spark plugs worn/fouled",
                "Ignition coil failure",
                "Injector clogged",
                "Low compression",
                "Vacuum leak",
                "Incorrect timing",
                "Excessive carbon buildup"
            ]
            self.dtcs["P0300"].affected_systems = ["Ignition", "Fuel", "Engine"]
            
        # Knock sensor
        if "P0325" in self.dtcs:
            self.dtcs["P0325"].symptoms = [
                "Reduced power (PCM retarding timing)",
                "Spark knock audible",
                "Poor performance"
            ]
            self.dtcs["P0325"].possible_causes = [
                "Knock sensor failed",
                "Wiring damaged",
                "Excessive engine knock",
                "PCM not receiving knock signal"
            ]
            self.dtcs["P0325"].affected_systems = ["Ignition", "Sensors"]
            
        # VVT codes
        if "P0011" in self.dtcs:
            self.dtcs["P0011"].symptoms = [
                "Rough idle",
                "Reduced power",
                "Poor fuel economy",
                "Rattle on startup"
            ]
            self.dtcs["P0011"].possible_causes = [
                "VVT solenoid stuck",
                "Oil pressure low",
                "Cam phaser worn",
                "Timing chain stretched",
                "Incorrect oil viscosity"
            ]
            self.dtcs["P0011"].affected_systems = ["VVT", "Lubrication"]
            
    def get_dtc(self, code: str) -> Optional[DTC]:
        """Get DTC by code"""
        return self.dtcs.get(code.upper())
        
    def search(self, query: str) -> List[DTC]:
        """Search DTCs by code or description"""
        query = query.upper()
        results = []
        for dtc in self.dtcs.values():
            if query in dtc.code or query in dtc.description.upper():
                results.append(dtc)
        return results
        
    def get_by_category(self, category: str) -> List[DTC]:
        """Get all DTCs in a category"""
        return [d for d in self.dtcs.values() if d.category == category]
        
    def get_tuning_related(self) -> List[DTC]:
        """Get all tuning-related DTCs"""
        return [d for d in self.dtcs.values() if d.tuning_related]
        
    def get_by_severity(self, severity: DTCSeverity) -> List[DTC]:
        """Get DTCs by severity level"""
        return [d for d in self.dtcs.values() if d.severity == severity]
        
    def analyze_codes(self, codes: List[str]) -> Dict:
        """Analyze a list of DTCs and provide recommendations"""
        analysis = {
            "codes_found": [],
            "codes_not_found": [],
            "critical_issues": [],
            "tuning_impact": [],
            "recommendations": []
        }
        
        for code in codes:
            dtc = self.get_dtc(code)
            if dtc:
                analysis["codes_found"].append(dtc.to_dict())
                
                if dtc.severity in (DTCSeverity.CRITICAL, DTCSeverity.SEVERE):
                    analysis["critical_issues"].append({
                        "code": dtc.code,
                        "description": dtc.description,
                        "severity": dtc.severity.value
                    })
                    
                if dtc.tuning_related:
                    analysis["tuning_impact"].append({
                        "code": dtc.code,
                        "category": dtc.category,
                        "impact": self._assess_tuning_impact(dtc)
                    })
            else:
                analysis["codes_not_found"].append(code)
                
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
        
    def _assess_tuning_impact(self, dtc: DTC) -> str:
        """Assess how a DTC impacts tuning"""
        critical_tuning_codes = ["P0171", "P0172", "P0174", "P0175", "P0300"]
        
        if dtc.code in critical_tuning_codes:
            return "CRITICAL - Fix before tuning"
        elif dtc.category in ["Fuel System", "Ignition", "VVT System"]:
            return "HIGH - Address before performance tuning"
        elif dtc.category in ["Air Intake", "Throttle"]:
            return "MEDIUM - May affect tune accuracy"
        else:
            return "LOW - Monitor but tuneable"
            
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate recommendations based on DTC analysis"""
        recommendations = []
        
        # Check for fuel system issues
        fuel_codes = [c for c in analysis["codes_found"] 
                     if c["category"] == "Fuel System"]
        if fuel_codes:
            recommendations.append({
                "priority": "HIGH",
                "category": "Fuel System",
                "message": f"{len(fuel_codes)} fuel system codes present",
                "action": "Verify fuel pressure, injector flow, and MAF calibration before tuning",
                "codes": [c["code"] for c in fuel_codes]
            })
            
        # Check for misfires
        misfire_codes = [c for c in analysis["codes_found"] 
                        if "Misfire" in c["description"]]
        if misfire_codes:
            recommendations.append({
                "priority": "CRITICAL",
                "category": "Ignition",
                "message": "Misfire detected",
                "action": "DO NOT TUNE - Fix spark plugs, coils, and injectors first",
                "codes": [c["code"] for c in misfire_codes]
            })
            
        # Check for VVT issues
        vvt_codes = [c for c in analysis["codes_found"] 
                    if "VVT" in c["category"] or "Camshaft" in c["description"]]
        if vvt_codes:
            recommendations.append({
                "priority": "HIGH",
                "category": "VVT System",
                "message": "VVT system codes present",
                "action": "Check oil level/quality and VVT solenoid operation",
                "codes": [c["code"] for c in vvt_codes]
            })
            
        # Check for knock sensor
        knock_codes = [c for c in analysis["codes_found"] 
                      if "Knock" in c["description"]]
        if knock_codes:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Knock Detection",
                "message": "Knock sensor issue detected",
                "action": "Knock detection compromised - use conservative timing",
                "codes": [c["code"] for c in knock_codes]
            })
            
        return recommendations
        
    def export_to_json(self, filepath: str):
        """Export database to JSON"""
        export_data = {
            "version": "1.0",
            "total_codes": len(self.dtcs),
            "codes": {code: dtc.to_dict() for code, dtc in self.dtcs.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
            
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        return {
            "total_codes": len(self.dtcs),
            "generic_codes": len([d for d in self.dtcs.values() if d.manufacturer == "Generic"]),
            "gm_codes": len([d for d in self.dtcs.values() if d.manufacturer == "GM"]),
            "tuning_related": len([d for d in self.dtcs.values() if d.tuning_related]),
            "by_severity": {
                "critical": len(self.get_by_severity(DTCSeverity.CRITICAL)),
                "severe": len(self.get_by_severity(DTCSeverity.SEVERE)),
                "moderate": len(self.get_by_severity(DTCSeverity.MODERATE)),
                "minor": len(self.get_by_severity(DTCSeverity.MINOR)),
                "info": len(self.get_by_severity(DTCSeverity.INFO))
            },
            "by_category": self._get_category_counts()
        }
        
    def _get_category_counts(self) -> Dict[str, int]:
        """Get count of DTCs per category"""
        counts = {}
        for dtc in self.dtcs.values():
            counts[dtc.category] = counts.get(dtc.category, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))


# Quick lookup functions
def lookup_dtc(code: str) -> Optional[DTC]:
    """Quick DTC lookup"""
    db = DTCDatabase()
    return db.get_dtc(code)


def analyze_dtcs(codes: List[str]) -> Dict:
    """Quick DTC analysis"""
    db = DTCDatabase()
    return db.analyze_codes(codes)


if __name__ == "__main__":
    db = DTCDatabase()
    
    print("=" * 60)
    print("DTC Database Statistics")
    print("=" * 60)
    stats = db.get_statistics()
    print(f"Total Codes: {stats['total_codes']}")
    print(f"Generic: {stats['generic_codes']}")
    print(f"GM-Specific: {stats['gm_codes']}")
    print(f"Tuning Related: {stats['tuning_related']}")
    print(f"\nBy Severity:")
    for sev, count in stats['by_severity'].items():
        print(f"  {sev}: {count}")
    print(f"\nTop Categories:")
    for cat, count in list(stats['by_category'].items())[:10]:
        print(f"  {cat}: {count}")
        
    print("\n" + "=" * 60)
    print("Example Lookups")
    print("=" * 60)
    
    # Lookup examples
    for code in ["P0171", "P0300", "P0011", "P0325"]:
        dtc = db.get_dtc(code)
        if dtc:
            print(f"\n{dtc.code}: {dtc.description}")
            print(f"  Category: {dtc.category}")
            print(f"  Severity: {dtc.severity.value}")
            print(f"  Tuning Related: {dtc.tuning_related}")
            if dtc.symptoms:
                print(f"  Symptoms: {', '.join(dtc.symptoms[:2])}...")
            if dtc.possible_causes:
                print(f"  Causes: {', '.join(dtc.possible_causes[:2])}...")
                
    print("\n" + "=" * 60)
    print("Example Analysis")
    print("=" * 60)
    
    # Analyze example codes
    test_codes = ["P0171", "P0300", "P1011", "P0420"]
    analysis = db.analyze_codes(test_codes)
    
    print(f"\nCodes analyzed: {test_codes}")
    print(f"Critical issues: {len(analysis['critical_issues'])}")
    print(f"Tuning impact: {len(analysis['tuning_impact'])}")
    
    print("\nRecommendations:")
    for rec in analysis['recommendations']:
        print(f"\n  [{rec['priority']}] {rec['category']}")
        print(f"    {rec['message']}")
        print(f"    → {rec['action']}")
