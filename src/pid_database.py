#!/usr/bin/env python3
"""
Comprehensive PID Database for GM Vehicles
Based on HP Tuners VCM Scanner and OBD-II standards
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import json


class PIDCategory(Enum):
    ENGINE = "Engine"
    FUEL = "Fuel System"
    SPARK = "Ignition"
    AIRFLOW = "Airflow"
    TRANSMISSION = "Transmission"
    TEMPERATURE = "Temperatures"
    ELECTRICAL = "Electrical"
    EMISSIONS = "Emissions"
    PERFORMANCE = "Performance"
    DIAGNOSTIC = "Diagnostic"


@dataclass
class PID:
    """Parameter ID definition"""
    name: str                    # Display name
    short_name: str             # Short code (e.g., "RPM")
    pid: Optional[str]          # OBD-II PID hex code
    mode: str                   # OBD-II Mode (01, 21, 22, etc.)
    category: PIDCategory
    unit: str
    description: str
    min_value: float
    max_value: float
    gm_specific: bool = False
    gm_pid: Optional[str] = None  # GM-specific extended PID
    conversion_formula: str = "raw"  # How to convert raw value
    equation: Optional[str] = None   # Math equation for display
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "short_name": self.short_name,
            "pid": self.pid,
            "mode": self.mode,
            "category": self.category.value,
            "unit": self.unit,
            "description": self.description,
            "min": self.min_value,
            "max": self.max_value,
            "gm_specific": self.gm_specific,
            "conversion": self.conversion_formula
        }


class PIDDatabase:
    """
    Comprehensive PID database for HP Tuners vehicles
    Includes standard OBD-II and GM-specific extended PIDs
    """
    
    def __init__(self):
        self.pids: Dict[str, PID] = {}
        self._initialize_standard_pids()
        self._initialize_gm_extended_pids()
        self._initialize_lfx_specific_pids()
        
    def _initialize_standard_pids(self):
        """Standard OBD-II PIDs (Mode 01)"""
        standard_pids = [
            # Engine
            PID("Engine RPM", "RPM", "0C", "01", PIDCategory.ENGINE, 
                "RPM", "Engine speed", 0, 8000, equation="(256*A+B)/4"),
            PID("Calculated Load", "ENGINE_LOAD", "04", "01", PIDCategory.ENGINE,
                "%", "Engine load calculated from airflow", 0, 100, equation="A*100/255"),
            PID("Throttle Position", "THROTTLE_POS", "11", "01", PIDCategory.ENGINE,
                "%", "Absolute throttle position", 0, 100, equation="A*100/255"),
            PID("Throttle Position B", "THROTTLE_POS_B", "45", "01", PIDCategory.ENGINE,
                "%", "Secondary throttle position", 0, 100, equation="A*100/255"),
            PID("Accelerator Pedal D", "PEDAL_POS_D", "49", "01", PIDCategory.ENGINE,
                "%", "Accelerator pedal position D", 0, 100, equation="A*100/255"),
            PID("Accelerator Pedal E", "PEDAL_POS_E", "4A", "01", PIDCategory.ENGINE,
                "%", "Accelerator pedal position E", 0, 100, equation="A*100/255"),
            PID("Engine Runtime", "RUN_TIME", "1F", "01", PIDCategory.ENGINE,
                "seconds", "Time since engine start", 0, 65535, equation="256*A+B"),
            
            # Vehicle
            PID("Vehicle Speed", "SPEED", "0D", "01", PIDCategory.PERFORMANCE,
                "km/h", "Vehicle speed", 0, 255, equation="A"),
            PID("Distance MIL On", "DISTANCE_MIL", "21", "01", PIDCategory.DIAGNOSTIC,
                "km", "Distance with MIL on", 0, 65535, equation="256*A+B"),
            PID("Distance Since DTC Cleared", "DISTANCE_SINCE_DTC", "31", "01", PIDCategory.DIAGNOSTIC,
                "km", "Distance since codes cleared", 0, 65535, equation="256*A+B"),
            
            # Fuel
            PID("MAF Rate", "MAF", "10", "01", PIDCategory.AIRFLOW,
                "g/s", "Mass airflow sensor rate", 0, 655, equation="(256*A+B)/100"),
            PID("Fuel Level", "FUEL_LEVEL", "2F", "01", PIDCategory.FUEL,
                "%", "Fuel tank level", 0, 100, equation="A*100/255"),
            PID("Short Term Fuel Trim B1", "STFT_B1", "06", "01", PIDCategory.FUEL,
                "%", "Short term fuel trim bank 1", -100, 99.2, equation="(A-128)*100/128"),
            PID("Long Term Fuel Trim B1", "LTFT_B1", "07", "01", PIDCategory.FUEL,
                "%", "Long term fuel trim bank 1", -100, 99.2, equation="(A-128)*100/128"),
            PID("Short Term Fuel Trim B2", "STFT_B2", "08", "01", PIDCategory.FUEL,
                "%", "Short term fuel trim bank 2", -100, 99.2, equation="(A-128)*100/128"),
            PID("Long Term Fuel Trim B2", "LTFT_B2", "09", "01", PIDCategory.FUEL,
                "%", "Long term fuel trim bank 2", -100, 99.2, equation="(A-128)*100/128"),
            PID("Fuel Rail Pressure", "FUEL_RAIL_PRESSURE", "23", "01", PIDCategory.FUEL,
                "kPa", "Fuel rail pressure (gauge)", 0, 655350, equation="(256*A+B)*10"),
            PID("Commanded Equivalence", "LAMBDA_CMD", "44", "01", PIDCategory.FUEL,
                "ratio", "Commanded equivalence ratio", 0, 2, equation="(256*A+B)/32768"),
            
            # O2 Sensors
            PID("O2 Sensor 1 B1", "O2_B1S1", "24", "01", PIDCategory.EMISSIONS,
                "ratio:V", "O2 sensor 1 bank 1", 0, 2, equation="(256*A+B)/32768:C/200-64"),
            PID("O2 Sensor 2 B1", "O2_B1S2", "25", "01", PIDCategory.EMISSIONS,
                "ratio:V", "O2 sensor 2 bank 1", 0, 2, equation="(256*A+B)/32768:C/200-64"),
            PID("O2 Sensor 1 B2", "O2_B2S1", "26", "01", PIDCategory.EMISSIONS,
                "ratio:V", "O2 sensor 1 bank 2", 0, 2, equation="(256*A+B)/32768:C/200-64"),
            PID("O2 Sensor 2 B2", "O2_B2S2", "27", "01", PIDCategory.EMISSIONS,
                "ratio:V", "O2 sensor 2 bank 2", 0, 2, equation="(256*A+B)/32768:C/200-64"),
            
            # Spark
            PID("Spark Advance", "SPARK_ADV", "0E", "01", PIDCategory.SPARK,
                "°BTDC", "Ignition timing advance", -64, 63.5, equation="A/2-64"),
            
            # Temps
            PID("Coolant Temp", "COOLANT_TEMP", "05", "01", PIDCategory.TEMPERATURE,
                "°C", "Engine coolant temperature", -40, 215, equation="A-40"),
            PID("Intake Air Temp", "INTAKE_TEMP", "0F", "01", PIDCategory.TEMPERATURE,
                "°C", "Intake air temperature", -40, 215, equation="A-40"),
            PID("Ambient Temp", "AMBIENT_TEMP", "46", "01", PIDCategory.TEMPERATURE,
                "°C", "Ambient air temperature", -40, 215, equation="A-40"),
            PID("Oil Temp", "OIL_TEMP", "5C", "01", PIDCategory.TEMPERATURE,
                "°C", "Engine oil temperature", -40, 215, equation="A-40"),
            
            # Airflow
            PID("MAP", "MAP", "0B", "01", PIDCategory.AIRFLOW,
                "kPa", "Manifold absolute pressure", 0, 255, equation="A"),
            PID("Barometric Pressure", "BARO", "33", "01", PIDCategory.AIRFLOW,
                "kPa", "Barometric pressure", 0, 255, equation="A"),
            
            # Electrical
            PID("Control Module Voltage", "BATTERY_VOLTAGE", "42", "01", PIDCategory.ELECTRICAL,
                "V", "Control module voltage", 0, 65.535, equation="(256*A+B)/1000"),
            PID("Commanded EVAP Purge", "EVAP_PURGE", "2E", "01", PIDCategory.EMISSIONS,
                "%", "Commanded evaporative purge", 0, 100, equation="A*100/255"),
            PID("Fuel Tank Pressure", "FUEL_TANK_PRESSURE", "32", "01", PIDCategory.EMISSIONS,
                "Pa", "Fuel tank pressure", -8192, 8192, equation="(256*A+B)/4-8192"),
        ]
        
        for pid in standard_pids:
            self.pids[pid.short_name] = pid
            
    def _initialize_gm_extended_pids(self):
        """GM Mode 22 Extended PIDs (requires HP Tuners Pro)"""
        gm_pids = [
            # Performance
            PID("Knock Retard", "KNOCK_RETARD", None, "22", PIDCategory.SPARK,
                "°", "Total knock retard being applied", 0, 20, 
                gm_specific=True, gm_pid="11A6", equation="A/16"),
            PID("Knock Sensor 1", "KNOCK_1", None, "22", PIDCategory.SPARK,
                "dB", "Knock sensor 1 signal level", 0, 255,
                gm_specific=True, gm_pid="11A0"),
            PID("Knock Sensor 2", "KNOCK_2", None, "22", PIDCategory.SPARK,
                "dB", "Knock sensor 2 signal level", 0, 255,
                gm_specific=True, gm_pid="11A1"),
            PID("Knock Sensor 3", "KNOCK_3", None, "22", PIDCategory.SPARK,
                "dB", "Knock sensor 3 signal level", 0, 255,
                gm_specific=True, gm_pid="11A2"),
            PID("Knock Sensor 4", "KNOCK_4", None, "22", PIDCategory.SPARK,
                "dB", "Knock sensor 4 signal level", 0, 255,
                gm_specific=True, gm_pid="11A3"),
            
            # Cylinder-specific knock (LFX V6)
            PID("Knock Retard Cyl 1", "KNOCK_CYL1", None, "22", PIDCategory.SPARK,
                "°", "Knock retard cylinder 1", 0, 20,
                gm_specific=True, gm_pid="11B0", equation="A/16"),
            PID("Knock Retard Cyl 2", "KNOCK_CYL2", None, "22", PIDCategory.SPARK,
                "°", "Knock retard cylinder 2", 0, 20,
                gm_specific=True, gm_pid="11B1", equation="A/16"),
            PID("Knock Retard Cyl 3", "KNOCK_CYL3", None, "22", PIDCategory.SPARK,
                "°", "Knock retard cylinder 3", 0, 20,
                gm_specific=True, gm_pid="11B2", equation="A/16"),
            PID("Knock Retard Cyl 4", "KNOCK_CYL4", None, "22", PIDCategory.SPARK,
                "°", "Knock retard cylinder 4", 0, 20,
                gm_specific=True, gm_pid="11B3", equation="A/16"),
            PID("Knock Retard Cyl 5", "KNOCK_CYL5", None, "22", PIDCategory.SPARK,
                "°", "Knock retard cylinder 5", 0, 20,
                gm_specific=True, gm_pid="11B4", equation="A/16"),
            PID("Knock Retard Cyl 6", "KNOCK_CYL6", None, "22", PIDCategory.SPARK,
                "°", "Knock retard cylinder 6", 0, 20,
                gm_specific=True, gm_pid="11B5", equation="A/16"),
            
            # Fuel System
            PID("Fuel Trim Cell", "FUEL_TRIM_CELL", None, "22", PIDCategory.FUEL,
                "", "Current fuel trim learning cell", 0, 22,
                gm_specific=True, gm_pid="1200"),
            PID("Injector Duty Cycle", "INJECTOR_DUTY", None, "22", PIDCategory.FUEL,
                "%", "Fuel injector duty cycle", 0, 100,
                gm_specific=True, gm_pid="1208", equation="A/2.55"),
            PID("Injector Pulse Width", "INJECTOR_PW", None, "22", PIDCategory.FUEL,
                "ms", "Fuel injector pulse width", 0, 50,
                gm_specific=True, gm_pid="1204", equation="(256*A+B)/64"),
            
            # Direct Injection (LFX)
            PID("High Pressure Fuel Pump", "HPFP_PRESSURE", None, "22", PIDCategory.FUEL,
                "MPa", "High pressure fuel pump output", 0, 35,
                gm_specific=True, gm_pid="120C", equation="(256*A+B)/128"),
            PID("HPFP Duty Cycle", "HPFP_DUTY", None, "22", PIDCategory.FUEL,
                "%", "High pressure fuel pump duty cycle", 0, 100,
                gm_specific=True, gm_pid="1210", equation="A/2.55"),
            PID("Fuel Rail Pressure DI", "FUEL_RAIL_DI", None, "22", PIDCategory.FUEL,
                "MPa", "Direct injection fuel rail pressure", 0, 35,
                gm_specific=True, gm_pid="1214", equation="(256*A+B)/128"),
            
            # VVT
            PID("Intake Cam Position", "VVT_INTAKE", None, "22", PIDCategory.ENGINE,
                "°", "Intake camshaft position", -90, 90,
                gm_specific=True, gm_pid="1300", equation="(A-128)*0.75"),
            PID("Exhaust Cam Position", "VVT_EXHAUST", None, "22", PIDCategory.ENGINE,
                "°", "Exhaust camshaft position", -90, 90,
                gm_specific=True, gm_pid="1304", equation="(A-128)*0.75"),
            PID("Intake Cam Solenoid", "VVT_INTAKE_CMD", None, "22", PIDCategory.ENGINE,
                "%", "Intake cam solenoid duty cycle", 0, 100,
                gm_specific=True, gm_pid="1308", equation="(A-128)/1.28"),
            PID("Exhaust Cam Solenoid", "VVT_EXHAUST_CMD", None, "22", PIDCategory.ENGINE,
                "%", "Exhaust cam solenoid duty cycle", 0, 100,
                gm_specific=True, gm_pid="130C", equation="(A-128)/1.28"),
            
            # Transmission
            PID("Transmission Gear", "GEAR", None, "22", PIDCategory.TRANSMISSION,
                "", "Current transmission gear", -1, 10,
                gm_specific=True, gm_pid="1400"),
            PID("Commanded Gear", "GEAR_CMD", None, "22", PIDCategory.TRANSMISSION,
                "", "Commanded transmission gear", -1, 10,
                gm_specific=True, gm_pid="1404"),
            PID("TCC State", "TCC_STATE", None, "22", PIDCategory.TRANSMISSION,
                "", "Torque converter clutch state", 0, 4,
                gm_specific=True, gm_pid="1408"),
            PID("TCC Slip", "TCC_SLIP", None, "22", PIDCategory.TRANSMISSION,
                "RPM", "Torque converter clutch slip", -1000, 1000,
                gm_specific=True, gm_pid="140C", equation="(256*A+B)/16-2048"),
            PID("Line Pressure", "LINE_PRESSURE", None, "22", PIDCategory.TRANSMISSION,
                "kPa", "Transmission line pressure", 0, 2000,
                gm_specific=True, gm_pid="1410", equation="(256*A+B)/8"),
            PID("Transmission Temp", "TRANS_TEMP", None, "22", PIDCategory.TEMPERATURE,
                "°C", "Transmission fluid temperature", -40, 215,
                gm_specific=True, gm_pid="1414", equation="A-40"),
            PID("Shift Time", "SHIFT_TIME", None, "22", PIDCategory.TRANSMISSION,
                "ms", "Last shift duration", 0, 1000,
                gm_specific=True, gm_pid="1418", equation="(256*A+B)/8"),
            PID("Turbine Speed", "TURBINE_SPEED", None, "22", PIDCategory.TRANSMISSION,
                "RPM", "Transmission input/turbine speed", 0, 10000,
                gm_specific=True, gm_pid="141C", equation="256*A+B"),
            PID("Output Speed", "OUTPUT_SPEED", None, "22", PIDCategory.TRANSMISSION,
                "RPM", "Transmission output speed", 0, 10000,
                gm_specific=True, gm_pid="1420", equation="256*A+B"),
            PID("Trans Slip", "TRANS_SLIP", None, "22", PIDCategory.TRANSMISSION,
                "RPM", "Transmission clutch slip", -1000, 1000,
                gm_specific=True, gm_pid="1424", equation="(256*A+B)/16-2048"),
            
            # Torque Management
            PID("Engine Torque", "ENGINE_TORQUE", None, "22", PIDCategory.PERFORMANCE,
                "Nm", "Current engine torque output", 0, 1500,
                gm_specific=True, gm_pid="1500", equation="256*A+B"),
            PID("Driver Torque Req", "TORQUE_REQ", None, "22", PIDCategory.PERFORMANCE,
                "Nm", "Driver requested torque", 0, 1500,
                gm_specific=True, gm_pid="1504", equation="256*A+B"),
            PID("Maximum Torque", "TORQUE_MAX", None, "22", PIDCategory.PERFORMANCE,
                "Nm", "Maximum available torque", 0, 1500,
                gm_specific=True, gm_pid="1508", equation="256*A+B"),
            PID("Torque Converter Load", "TCC_LOAD", None, "22", PIDCategory.TRANSMISSION,
                "Nm", "Torque on converter", 0, 1500,
                gm_specific=True, gm_pid="150C", equation="256*A+B"),
            
            # Airflow Advanced
            PID("Cylinder Air Mass", "AIR_MASS", None, "22", PIDCategory.AIRFLOW,
                "mg", "Air mass per cylinder", 0, 1500,
                gm_specific=True, gm_pid="1600", equation="256*A+B"),
            PID("VE Current", "VE", None, "22", PIDCategory.AIRFLOW,
                "%", "Current volumetric efficiency", 0, 100,
                gm_specific=True, gm_pid="1604", equation="A/2.55"),
            PID("Desired Idle", "IDLE_DESIRED", None, "22", PIDCategory.ENGINE,
                "RPM", "Desired idle speed", 0, 3000,
                gm_specific=True, gm_pid="1608", equation="(256*A+B)/4"),
            PID("Idle Airflow", "IDLE_AIRFLOW", None, "22", PIDCategory.AIRFLOW,
                "g/s", "Current idle airflow", 0, 100,
                gm_specific=True, gm_pid="160C", equation="(256*A+B)/100"),
            
            # Temps Extended
            PID("Cylinder Head Temp", "CHT", None, "22", PIDCategory.TEMPERATURE,
                "°C", "Cylinder head temperature", -40, 215,
                gm_specific=True, gm_pid="1700", equation="A-40"),
            PID("Trans Oil Temp", "TRANS_OIL_TEMP", None, "22", PIDCategory.TEMPERATURE,
                "°C", "Transmission oil temperature", -40, 215,
                gm_specific=True, gm_pid="1704", equation="A-40"),
            PID("IAT Sensor 2", "IAT2", None, "22", PIDCategory.TEMPERATURE,
                "°C", "Intake air temp (post-intercooler)", -40, 215,
                gm_specific=True, gm_pid="1708", equation="A-40"),
        ]
        
        for pid in gm_pids:
            self.pids[pid.short_name] = pid
            
    def _initialize_lfx_specific_pids(self):
        """LFX 3.6L V6 Specific PIDs"""
        lfx_pids = [
            PID("LFX Fuel Pressure Actual", "LFX_FP_ACTUAL", None, "22", PIDCategory.FUEL,
                "MPa", "LFX actual fuel pressure", 0, 35,
                gm_specific=True, gm_pid="2200", equation="(256*A+B)/128"),
            PID("LFX Fuel Pressure Desired", "LFX_FP_DESIRED", None, "22", PIDCategory.FUEL,
                "MPa", "LFX desired fuel pressure", 0, 35,
                gm_specific=True, gm_pid="2204", equation="(256*A+B)/128"),
            PID("LFX Cam Angle Intake B1", "LFX_CAM_INT_B1", None, "22", PIDCategory.ENGINE,
                "°", "Intake cam bank 1 angle", -60, 60,
                gm_specific=True, gm_pid="2208"),
            PID("LFX Cam Angle Intake B2", "LFX_CAM_INT_B2", None, "22", PIDCategory.ENGINE,
                "°", "Intake cam bank 2 angle", -60, 60,
                gm_specific=True, gm_pid="220C"),
        ]
        
        for pid in lfx_pids:
            self.pids[pid.short_name] = pid
            
    def get_pid(self, short_name: str) -> Optional[PID]:
        """Get PID by short name"""
        return self.pids.get(short_name)
        
    def get_by_category(self, category: PIDCategory) -> List[PID]:
        """Get all PIDs in a category"""
        return [p for p in self.pids.values() if p.category == category]
        
    def get_essential_logging_pids(self) -> List[PID]:
        """Get essential PIDs for baseline logging"""
        essential = [
            "RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "PEDAL_POS",
            "MAF", "MAP", "STFT_B1", "LTFT_B1", "O2_B1S1",
            "SPARK_ADV", "COOLANT_TEMP", "INTAKE_TEMP", "BATTERY_VOLTAGE"
        ]
        return [self.pids[name] for name in essential if name in self.pids]
        
    def get_performance_pids(self) -> List[PID]:
        """Get PIDs for performance tuning"""
        perf = [
            "RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "PEDAL_POS",
            "KNOCK_RETARD", "KNOCK_CYL1", "KNOCK_CYL2", "KNOCK_CYL3",
            "KNOCK_CYL4", "KNOCK_CYL5", "KNOCK_CYL6",
            "STFT_B1", "LTFT_B1", "STFT_B2", "LTFT_B2",
            "FUEL_TRIM_CELL", "INJECTOR_DUTY", "HPFP_PRESSURE",
            "SPARK_ADV", "VVT_INTAKE", "VVT_EXHAUST",
            "MAF", "AIR_MASS", "VE",
            "ENGINE_TORQUE", "TORQUE_REQ", "TORQUE_MAX",
            "GEAR", "TCC_STATE", "TCC_SLIP", "TRANS_TEMP"
        ]
        return [self.pids[name] for name in perf if name in self.pids]
        
    def get_lfx_logging_pids(self) -> List[PID]:
        """Get complete LFX V6 logging list"""
        lfx_list = [
            # Standard
            "RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "PEDAL_POS",
            "MAF", "MAP", "BARO", "COOLANT_TEMP", "INTAKE_TEMP",
            "STFT_B1", "LTFT_B1", "STFT_B2", "LTFT_B2",
            "O2_B1S1", "O2_B2S1", "SPARK_ADV",
            # GM Extended
            "KNOCK_RETARD", "KNOCK_CYL1", "KNOCK_CYL2", "KNOCK_CYL3",
            "KNOCK_CYL4", "KNOCK_CYL5", "KNOCK_CYL6",
            "FUEL_TRIM_CELL", "INJECTOR_DUTY", "INJECTOR_PW",
            "HPFP_PRESSURE", "HPFP_DUTY", "FUEL_RAIL_DI",
            "VVT_INTAKE", "VVT_EXHAUST", "VVT_INTAKE_CMD", "VVT_EXHAUST_CMD",
            "AIR_MASS", "VE", "IDLE_AIRFLOW",
            "GEAR", "GEAR_CMD", "TCC_STATE", "TCC_SLIP",
            "LINE_PRESSURE", "TRANS_TEMP", "SHIFT_TIME",
            "TURBINE_SPEED", "OUTPUT_SPEED", "TRANS_SLIP",
            "ENGINE_TORQUE", "TORQUE_REQ", "TORQUE_MAX",
            "CHT", "OIL_TEMP"
        ]
        return [self.pids[name] for name in lfx_list if name in self.pids]
        
    def search(self, query: str) -> List[PID]:
        """Search PIDs by name or description"""
        query = query.lower()
        results = []
        for pid in self.pids.values():
            if (query in pid.name.lower() or 
                query in pid.short_name.lower() or
                query in pid.description.lower()):
                results.append(pid)
        return results
        
    def export_to_json(self, filepath: str):
        """Export entire database to JSON"""
        export_data = {
            "version": "1.0",
            "total_pids": len(self.pids),
            "categories": [cat.value for cat in PIDCategory],
            "pids": {name: pid.to_dict() for name, pid in self.pids.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
            
    def get_pid_list_for_vcm_scanner(self) -> List[str]:
        """Get formatted list for VCM Scanner configuration"""
        lines = []
        for pid in sorted(self.pids.values(), key=lambda p: (p.category.value, p.name)):
            if pid.gm_specific and pid.gm_pid:
                lines.append(f"Mode {pid.mode} PID {pid.gm_pid}: {pid.name} ({pid.unit})")
            elif pid.pid:
                lines.append(f"Mode {pid.mode} PID {pid.pid}: {pid.name} ({pid.unit})")
        return lines


# Predefined logging configurations
LOGGING_PRESETS = {
    "baseline": {
        "description": "Essential parameters for baseline logging",
        "interval": 0.5,
        "pids": ["RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "MAF",
                "STFT_B1", "LTFT_B1", "SPARK_ADV", "COOLANT_TEMP", "INTAKE_TEMP"]
    },
    "performance": {
        "description": "Full performance analysis including knock",
        "interval": 0.1,
        "pids": ["RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "PEDAL_POS",
                "KNOCK_RETARD", "STFT_B1", "LTFT_B1", "SPARK_ADV",
                "MAF", "HPFP_PRESSURE", "VVT_INTAKE", "GEAR", "TCC_STATE",
                "ENGINE_TORQUE", "TRANS_TEMP"]
    },
    "lfx_full": {
        "description": "Complete LFX V6 monitoring",
        "interval": 0.1,
        "pids": ["RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "PEDAL_POS",
                "KNOCK_RETARD", "KNOCK_CYL1", "KNOCK_CYL2", "KNOCK_CYL3",
                "KNOCK_CYL4", "KNOCK_CYL5", "KNOCK_CYL6",
                "STFT_B1", "LTFT_B1", "STFT_B2", "LTFT_B2",
                "FUEL_TRIM_CELL", "INJECTOR_DUTY", "HPFP_PRESSURE",
                "SPARK_ADV", "VVT_INTAKE", "VVT_EXHAUST",
                "MAF", "AIR_MASS", "CHT", "OIL_TEMP",
                "GEAR", "TCC_STATE", "TCC_SLIP", "TRANS_TEMP", "SHIFT_TIME"]
    },
    "transmission": {
        "description": "Transmission diagnostics",
        "interval": 0.2,
        "pids": ["RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS", "GEAR",
                "GEAR_CMD", "TCC_STATE", "TCC_SLIP", "LINE_PRESSURE",
                "TRANS_TEMP", "SHIFT_TIME", "TURBINE_SPEED", "OUTPUT_SPEED"]
    }
}


if __name__ == "__main__":
    db = PIDDatabase()
    
    print(f"Total PIDs: {len(db.pids)}")
    print("\nEssential Logging PIDs:")
    for pid in db.get_essential_logging_pids():
        print(f"  - {pid.short_name}: {pid.name} ({pid.unit})")
        
    print("\nLFX Performance PIDs:")
    for pid in db.get_lfx_logging_pids()[:15]:
        print(f"  - {pid.short_name}: {pid.name}")
        
    print("\nSearch 'knock':")
    for pid in db.search("knock")[:5]:
        print(f"  - {pid.short_name}: {pid.name}")
