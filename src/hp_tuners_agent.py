#!/usr/bin/env python3
"""
HP Tuners Master Agent
Comprehensive ECU tuning, transmission tuning, and data analysis system
"""

import obd
import time
import json
import csv
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ECUParameters:
    """ECU identification and configuration"""
    vin: str = "Unknown"
    calibration_id: str = "Unknown"
    os_version: str = "Unknown"
    fuel_type: str = "Gasoline"
    displacement: float = 6.2  # Liters
    cylinder_count: int = 8
    boost_enabled: bool = False
    flex_fuel_enabled: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TuneData:
    """Complete tune structure"""
    spark_advance: Dict[str, Dict[str, float]]  # Load -> RPM -> degrees
    fuel_mass: Dict[str, Dict[str, float]]      # Load -> RPM -> mg
    airflow: Dict[str, List[Tuple[float, float]]]  # MAF voltage -> g/s
    torque_limits: Dict[str, int]               # Gear -> Nm limit
    transmission: Dict[str, any]                # TCM data
    safety_limits: Dict[str, any]               # Rev limiter, etc.
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TCMParameters:
    """Transmission Control Module data"""
    shift_points: Dict[str, Dict[str, int]]     # Mode -> Gear -> RPM
    line_pressure: int                         # PSI
    converter_lockup: Dict[str, bool]          # Gear -> enabled
    torque_management: int                     # Percentage
    shift_time_target: float                     # Seconds
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ECUController:
    """Main ECU communication and control class"""
    
    def __init__(self, port: str = None, protocol: str = None):
        self.port = port
        self.protocol = protocol
        self.connection: Optional[obd.OBD] = None
        self.ecu_info: Optional[ECUParameters] = None
        self.current_tune: Optional[TuneData] = None
        self.data_log: List[Dict] = []
        self.tcm: Optional[TCMParameters] = None
        self.connected = False
        
    def connect(self, timeout: int = 30) -> bool:
        """Connect to OBD-II adapter"""
        try:
            if self.port:
                self.connection = obd.OBD(self.port, protocol=self.protocol, timeout=timeout)
            else:
                # Auto-detect Bluetooth or USB
                self.connection = obd.OBD(timeout=timeout)
            
            self.connected = self.connection.is_connected()
            if self.connected:
                logger.info(f"Connected to ECU via {self.connection.port_name()}")
            else:
                logger.error("Failed to connect to ECU")
            return self.connected
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from ECU"""
        if self.connection:
            self.connection.close()
            self.connected = False
            logger.info("Disconnected from ECU")
    
    def read_ecu_info(self) -> ECUParameters:
        """Read basic ECU identification"""
        if not self.connected:
            raise ConnectionError("Not connected to ECU")
        
        info = ECUParameters()
        
        # Read VIN
        vin_cmd = obd.commands.VIN
        response = self.connection.query(vin_cmd)
        if response.is_successful():
            info.vin = str(response.value)
        
        # Read calibration ID (Mode 09 PID 04)
        try:
            cal_cmd = obd.commands.CALIBRATION_ID
            response = self.connection.query(cal_cmd)
            if response.is_successful():
                info.calibration_id = str(response.value)
        except:
            logger.warning("Calibration ID not available")
        
        # Read ECU name (Mode 09 PID 0A)
        try:
            ecu_name_cmd = obd.commands.ECU_NAME
            response = self.connection.query(ecu_name_cmd)
            if response.is_successful():
                info.os_version = str(response.value)
        except:
            logger.warning("ECU name not available")
        
        self.ecu_info = info
        logger.info(f"ECU Info: VIN={info.vin}, CAL={info.calibration_id}")
        return info
    
    def start_data_logging(self, pids: List[str], duration: int = 300, interval: float = 0.5) -> List[Dict]:
        """Log specified PIDs for duration seconds"""
        if not self.connected:
            raise ConnectionError("Not connected to ECU")
        
        self.data_log = []
        start_time = time.time()
        sample_count = 0
        
        logger.info(f"Starting data logging for {duration} seconds...")
        
        while time.time() - start_time < duration:
            entry = {
                "timestamp": time.time(),
                "elapsed": time.time() - start_time
            }
            
            for pid in pids:
                try:
                    # Try to get command from obd.commands
                    cmd = getattr(obd.commands, pid.upper(), None)
                    if cmd:
                        response = self.connection.query(cmd)
                        if response.is_successful() and response.value is not None:
                            # Extract magnitude if it's a Quantity
                            if hasattr(response.value, 'magnitude'):
                                entry[pid] = response.value.magnitude
                            else:
                                entry[pid] = response.value
                        else:
                            entry[pid] = None
                    else:
                        entry[pid] = None
                except Exception as e:
                    entry[pid] = None
                    logger.debug(f"Error reading {pid}: {e}")
            
            self.data_log.append(entry)
            sample_count += 1
            time.sleep(interval)
        
        logger.info(f"Logging complete: {sample_count} samples collected")
        return self.data_log
    
    def export_log_to_csv(self, filepath: Path, log_data: List[Dict] = None):
        """Export data log to CSV file"""
        data = log_data or self.data_log
        if not data:
            logger.warning("No data to export")
            return
        
        # Get all unique keys
        keys = set()
        for entry in data:
            keys.update(entry.keys())
        keys = sorted(keys)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Exported {len(data)} records to {filepath}")
    
    def analyze_knock(self, log_data: List[Dict] = None) -> Dict:
        """Analyze knock sensor data from logs"""
        data = log_data or self.data_log
        
        # Look for knock-related data (may be PID KNOCK, SPARK_ADV, etc.)
        knock_events = []
        for entry in data:
            if 'KNOCK' in entry and entry['KNOCK'] is not None and entry['KNOCK'] > 0:
                knock_events.append(entry)
            elif 'KNOCK_RETARD' in entry and entry['KNOCK_RETARD'] is not None and entry['KNOCK_RETARD'] > 0:
                knock_events.append(entry)
        
        analysis = {
            "total_events": len(knock_events),
            "max_knock": 0,
            "rpm_at_knock": [],
            "knock_by_rpm": {},
            "recommendation": ""
        }
        
        if knock_events:
            knock_values = [e.get('KNOCK', e.get('KNOCK_RETARD', 0)) for e in knock_events]
            analysis["max_knock"] = max(knock_values)
            analysis["rpm_at_knock"] = [e.get('RPM') for e in knock_events if e.get('RPM')]
            
            # Group by RPM ranges
            for e in knock_events:
                rpm = e.get('RPM')
                if rpm:
                    rpm_range = int(rpm / 500) * 500
                    if rpm_range not in analysis["knock_by_rpm"]:
                        analysis["knock_by_rpm"][rpm_range] = []
                    analysis["knock_by_rpm"][rpm_range].append(e.get('KNOCK', 0))
        
        analysis["recommendation"] = self._knock_recommendation(
            analysis["total_events"], 
            analysis["max_knock"]
        )
        
        return analysis
    
    def _knock_recommendation(self, event_count: int, max_knock: float) -> str:
        """Generate recommendation based on knock analysis"""
        if event_count == 0:
            return "No knock detected - timing can be advanced 2-4 degrees for more power"
        elif event_count < 5 and max_knock < 2:
            return "Minor knock detected - reduce timing 1-2 degrees in affected RPM range"
        elif event_count < 10 and max_knock < 4:
            return "Moderate knock - reduce timing 2-4 degrees, check fuel quality (use 93 octane)"
        else:
            return "Significant knock detected - reduce timing 4-6 degrees immediately, check for mechanical issues"
    
    def analyze_fuel_trims(self, log_data: List[Dict] = None) -> Dict:
        """Analyze fuel trims for tuning recommendations"""
        data = log_data or self.data_log
        
        stft_values = []
        ltft_values = []
        
        for entry in data:
            stft = entry.get('SHORT_FUEL_TRIM') or entry.get('SHRTFT1')
            ltft = entry.get('LONG_FUEL_TRIM') or entry.get('LONGFT1')
            
            if stft is not None:
                stft_values.append(stft)
            if ltft is not None:
                ltft_values.append(ltft)
        
        analysis = {
            "sample_count": len(stft_values),
            "short_term_avg": sum(stft_values) / len(stft_values) if stft_values else 0,
            "long_term_avg": sum(ltft_values) / len(ltft_values) if ltft_values else 0,
            "max_stft": max(stft_values) if stft_values else 0,
            "min_stft": min(stft_values) if stft_values else 0,
            "fuel_correction_needed": False,
            "recommendation": ""
        }
        
        stft_avg = analysis["short_term_avg"]
        if abs(stft_avg) < 3:
            analysis["recommendation"] = "Fuel trims optimal - no adjustment needed"
        elif stft_avg > 5:
            analysis["recommendation"] = f"Running lean (STFT +{stft_avg:.1f}%) - increase fuel mass 4-6%"
            analysis["fuel_correction_needed"] = True
        elif stft_avg < -5:
            analysis["recommendation"] = f"Running rich (STFT {stft_avg:.1f}%) - decrease fuel mass 4-6%"
            analysis["fuel_correction_needed"] = True
        else:
            analysis["recommendation"] = f"Minor fuel adjustment recommended (STFT {stft_avg:.1f}%)"
        
        return analysis
    
    def export_to_hp_tuners_format(self, output_path: Path):
        """Export current tune to HP Tuners compatible JSON format"""
        if not self.ecu_info:
            logger.warning("No ECU info available for export")
        
        tune_export = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "tool": "HP Tuners Master Agent",
                "version": "1.0"
            },
            "vehicle": self.ecu_info.to_dict() if self.ecu_info else {},
            "tune": self.current_tune.to_dict() if self.current_tune else {},
            "tcm": self.tcm.to_dict() if self.tcm else {}
        }
        
        with open(output_path, 'w') as f:
            json.dump(tune_export, f, indent=2)
        
        logger.info(f"Exported tune to {output_path}")


class TCMController:
    """Transmission Control Module operations"""
    
    def __init__(self, ecu_controller: ECUController):
        self.ecu = ecu_controller
        self.tcm_data: Optional[TCMParameters] = None
    
    def read_tcm_calibration(self) -> TCMParameters:
        """Read TCM configuration"""
        # In reality, many TCM parameters require manufacturer-specific PIDs
        # This is a template structure
        
        self.tcm_data = TCMParameters(
            shift_points={
                "normal": {
                    "1_2": 5500, "2_3": 5800, "3_4": 6000,
                    "4_5": 6200, "5_6": 6400, "6_7": 6600, "7_8": 6800
                },
                "sport": {
                    "1_2": 6500, "2_3": 6800, "3_4": 7000,
                    "4_5": 7200, "5_6": 7400, "6_7": 7600, "7_8": 7800
                }
            },
            line_pressure=85,
            converter_lockup={
                "3": True, "4": True, "5": True,
                "6": True, "7": True, "8": True
            },
            torque_management=100,
            shift_time_target=0.25
        )
        
        return self.tcm_data
    
    def create_performance_profile(self, base_profile: Dict, increase: int = 800) -> Dict:
        """Generate performance shift points"""
        performance = {}
        for gear_shift, rpm in base_profile.items():
            # Raise shift points
            new_rpm = min(rpm + increase, 7800)  # Safety cap
            performance[gear_shift] = new_rpm
        return performance
    
    def optimize_drag_race(self) -> TCMParameters:
        """Maximum performance for drag racing"""
        return TCMParameters(
            shift_points={
                "launch": {
                    "1_2": 6800, "2_3": 7000,
                    "3_4": 7200, "4_5": 7400
                }
            },
            line_pressure=120,  # Firmer shifts
            converter_lockup={
                "2": False, "3": False, "4": True,
                "5": False, "6": False
            },
            torque_management=50,  # Less torque reduction
            shift_time_target=0.15  # Quicker shifts
        )
    
    def optimize_daily_drive(self) -> TCMParameters:
        """Smooth, efficient daily driving"""
        return TCMParameters(
            shift_points={
                "normal": {
                    "1_2": 4500, "2_3": 4800, "3_4": 5000,
                    "4_5": 5200, "5_6": 5500, "6_7": 5800, "7_8": 6000
                }
            },
            line_pressure=80,  # Softer shifts
            converter_lockup={
                "2": True, "3": True, "4": True,
                "5": True, "6": True, "7": True, "8": True
            },
            torque_management=100,
            shift_time_target=0.40  # Comfort priority
        )


class TuneAnalyzer:
    """Advanced data analysis for tuning decisions"""
    
    def __init__(self, log_data: List[Dict]):
        self.data = log_data
    
    def find_max_power_rpm(self) -> Optional[int]:
        """Estimate RPM at peak power based on airflow"""
        max_airflow = 0
        max_rpm = None
        
        for entry in self.data:
            rpm = entry.get('RPM')
            maf = entry.get('MAF') or entry.get('MAF_RATE')
            
            if rpm and maf and maf > max_airflow:
                max_airflow = maf
                max_rpm = int(rpm)
        
        return max_rpm
    
    def calculate_average_load(self) -> float:
        """Calculate average engine load from logs"""
        loads = [e.get('ENGINE_LOAD') for e in self.data if e.get('ENGINE_LOAD')]
        return sum(loads) / len(loads) if loads else 0
    
    def identify_wot_events(self, tps_threshold: float = 80.0) -> List[Dict]:
        """Identify wide open throttle events"""
        wot_events = []
        
        for entry in self.data:
            tps = entry.get('THROTTLE_POS') or entry.get('THROTTLE_POSITION')
            if tps and tps >= tps_threshold:
                wot_events.append(entry)
        
        return wot_events
    
    def analyze_wot_afr(self) -> Dict:
        """Analyze air-fuel ratio during WOT"""
        wot_events = self.identify_wot_events()
        
        if not wot_events:
            return {"error": "No WOT events found"}
        
        o2_values = []
        for e in wot_events:
            o2 = e.get('O2_B1S1') or e.get('O2_SENSOR_1')
            if o2:
                o2_values.append(o2)
        
        if not o2_values:
            return {"error": "No O2 sensor data available"}
        
        avg_o2 = sum(o2_values) / len(o2_values)
        
        # Convert O2 voltage to approximate AFR (simplified)
        # This is vehicle-specific and requires wideband for accuracy
        approx_afr = 14.7 - (avg_o2 - 0.45) * 10  # Very rough approximation
        
        return {
            "wot_samples": len(o2_values),
            "avg_o2_voltage": avg_o2,
            "approx_afr": approx_afr,
            "recommendation": "Use wideband for accurate AFR measurement"
        }


class SafetyValidator:
    """Validate tune safety before flashing"""
    
    @staticmethod
    def validate_flash(tune: TuneData, ecu_info: ECUParameters, backups_dir: Path) -> Dict:
        """Run pre-flash safety checks"""
        
        checks = {
            "stock_backup_exists": False,
            "fuel_system_capacity": True,
            "spark_advance_safe": True,
            "rev_limiter_safe": True,
            "torque_limits_safe": True
        }
        
        recommendations = []
        safe = True
        
        # Check for stock backup
        stock_backup = backups_dir / f"{ecu_info.vin}_stock.json"
        checks["stock_backup_exists"] = stock_backup.exists()
        
        if not checks["stock_backup_exists"]:
            recommendations.append("CRITICAL: No stock backup found! Read and save stock tune before flashing.")
            safe = False
        
        # Check fuel demands
        if tune and tune.fuel_mass:
            max_fuel = max(max(table.values()) for table in tune.fuel_mass.values())
            if max_fuel > 150:  # Typical limit for stock injectors
                checks["fuel_system_capacity"] = False
                recommendations.append(f"WARNING: Fuel demand ({max_fuel:.1f} mg) may exceed injector capacity")
                safe = False
        
        # Check spark advance
        if tune and tune.spark_advance:
            max_spark = max(max(table.values()) for table in tune.spark_advance.values())
            if max_spark > 50:
                checks["spark_advance_safe"] = False
                recommendations.append(f"WARNING: Very high spark advance ({max_spark}°) - risk of knock")
        
        # Check safety limits
        if tune and tune.safety_limits:
            rev_limit = tune.safety_limits.get('rev_limiter', 7000)
            if rev_limit > 7500:
                checks["rev_limiter_safe"] = False
                recommendations.append(f"WARNING: Rev limiter ({rev_limit}) exceeds safe mechanical limit")
        
        return {
            "safe_to_flash": safe,
            "checks": checks,
            "recommendations": recommendations,
            "can_proceed": safe or input("Override safety checks? (y/n): ").lower() == 'y'
        }


class HPTunersAgent:
    """Main agent class combining all functionality"""
    
    def __init__(self, port: str = None, backups_dir: str = "./tune_backups"):
        self.port = port
        self.ecu = ECUController(port)
        self.tcm = None
        self.backups_dir = Path(backups_dir)
        self.backups_dir.mkdir(exist_ok=True)
        self.analyzer = None
    
    def initialize(self) -> bool:
        """Initialize connection to vehicle"""
        if not self.ecu.connect():
            logger.error("Failed to connect to vehicle")
            return False
        
        # Read ECU info
        self.ecu.read_ecu_info()
        
        # Initialize TCM controller
        self.tcm = TCMController(self.ecu)
        self.tcm.read_tcm_calibration()
        
        return True
    
    def backup_stock_tune(self) -> Path:
        """Read and backup current ECU tune"""
        if not self.ecu.connected:
            raise ConnectionError("Not connected")
        
        backup_file = self.backups_dir / f"{self.ecu.ecu_info.vin}_stock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Note: Full ECU reading requires special hardware (MPVI)
        # This saves what we can read via OBD
        self.ecu.export_to_hp_tuners_format(backup_file)
        
        logger.info(f"Stock tune backed up to {backup_file}")
        return backup_file
    
    def log_baseline(self, duration: int = 600, output: str = None) -> Path:
        """Log baseline data from vehicle"""
        essential_pids = [
            "RPM", "SPEED", "ENGINE_LOAD", "THROTTLE_POS",
            "MAF", "O2_B1S1", "O2_B2S1",
            "SHORT_FUEL_TRIM", "LONG_FUEL_TRIM",
            "SPARK_ADV", "COOLANT_TEMP", "INTAKE_TEMP"
        ]
        
        logger.info(f"Starting baseline logging for {duration} seconds...")
        logger.info("Drive normally including: idle, cruise, and WOT acceleration")
        
        log_data = self.ecu.start_data_logging(essential_pids, duration)
        
        # Analyze
        self.analyzer = TuneAnalyzer(log_data)
        
        knock_analysis = self.ecu.analyze_knock(log_data)
        fuel_analysis = self.ecu.analyze_fuel_trims(log_data)
        max_power_rpm = self.analyzer.find_max_power_rpm()
        
        logger.info(f"\n=== Baseline Analysis ===")
        logger.info(f"Peak power RPM estimate: {max_power_rpm}")
        logger.info(f"Knock events: {knock_analysis['total_events']}")
        logger.info(f"Fuel trim recommendation: {fuel_analysis['recommendation']}")
        
        # Export to CSV
        if output:
            output_path = Path(output)
        else:
            output_path = self.backups_dir / f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.ecu.export_log_to_csv(output_path, log_data)
        
        return output_path
    
    def create_stage1_tune(self, mods: List[str]) -> TuneData:
        """Create safe Stage 1 tune for basic bolt-ons"""
        # Start with stock or baseline
        # This is a template - actual implementation requires ECU read
        
        spark = {}
        for load in [20, 40, 60, 80, 100]:
            spark[str(load)] = {}
            for rpm in range(1000, 7000, 500):
                # Add 2 degrees timing
                base = 20 + (rpm / 1000) * 2
                spark[str(load)][str(rpm)] = min(base + 2, 50)
        
        fuel = {}
        for load in [20, 40, 60, 80, 100]:
            fuel[str(load)] = {}
            for rpm in range(1000, 7000, 500):
                # Slight enrichment
                base = 50 + load
                fuel[str(load)][str(rpm)] = base * 0.97
        
        tune = TuneData(
            spark_advance=spark,
            fuel_mass=fuel,
            airflow={
                "maf": [(0, 0), (1, 12), (2, 30), (3, 60), (4, 100), (5, 160)]
            },
            torque_limits={
                "1": 600, "2": 650, "3": 700,
                "4": 750, "5": 800, "6": 850
            },
            transmission={},
            safety_limits={
                "rev_limiter": 6800,
                "fuel_cut": 7000,
                "cooling_fan_low": 95,
                "cooling_fan_high": 105
            }
        )
        
        logger.info("Stage 1 tune created")
        logger.info("Modifications supported: Cold air intake, cat-back exhaust")
        
        return tune
    
    def validate_and_export(self, tune: TuneData, output: str) -> bool:
        """Validate tune and export to HP Tuners format"""
        
        # Safety check
        validator = SafetyValidator()
        result = validator.validate_flash(tune, self.ecu.ecu_info, self.backups_dir)
        
        if not result["safe_to_flash"]:
            logger.warning("Safety issues found:")
            for rec in result["recommendations"]:
                logger.warning(f"  - {rec}")
        
        if result["can_proceed"]:
            self.ecu.current_tune = tune
            self.ecu.export_to_hp_tuners_format(Path(output))
            logger.info(f"Tune exported to {output}")
            return True
        else:
            logger.error("Export cancelled due to safety concerns")
            return False
    
    def shutdown(self):
        """Clean shutdown"""
        if self.ecu:
            self.ecu.disconnect()
        logger.info("HP Tuners Agent shutdown complete")


def main():
    """Example usage"""
    print("HP Tuners Master Agent v1.0")
    print("===========================\n")
    
    # Initialize agent
    agent = HPTunersAgent()
    
    print("1. Connect to vehicle")
    if not agent.initialize():
        print("Failed to connect. Ensure OBD-II adapter is paired/connected.")
        return
    
    print(f"Connected: VIN={agent.ecu.ecu_info.vin}")
    
    print("\n2. Backup stock tune")
    backup_file = agent.backup_stock_tune()
    print(f"Backup saved: {backup_file}")
    
    print("\n3. Log baseline data")
    print("Drive the vehicle normally for 10 minutes...")
    log_file = agent.log_baseline(duration=600)
    print(f"Log saved: {log_file}")
    
    print("\n4. Create Stage 1 tune")
    tune = agent.create_stage1_tune(mods=["intake", "exhaust"])
    
    print("\n5. Validate and export")
    output_file = f"stage1_{agent.ecu.ecu_info.vin}.json"
    if agent.validate_and_export(tune, output_file):
        print(f"Tune ready: {output_file}")
        print("\nNext steps:")
        print("- Open in HP Tuners Editor")
        print("- Verify tables match your modifications")
        print("- Flash to vehicle using MPVI")
        print("- Log and verify results")
    
    agent.shutdown()


if __name__ == "__main__":
    main()