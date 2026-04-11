---
name: hp-tuners-master
description: Comprehensive AI agent for HP Tuners vehicle tuning - ECU read/write, transmission tuning, data analysis, and OBD-II integration
domain: automotive, tuning, diagnostics
tools_needed: [terminal, file, execute_code, web]
requires: python-obd, python-can, pandas, numpy
---

# HP Tuners Master AI Agent

Complete system for ECU tuning, transmission tuning, data logging, and vehicle diagnostics using HP Tuners and OBD-II protocols.

## Capabilities

### 1. ECU Operations
- **Read ECU**: Extract current tune, stock calibration, VIN, and module info
- **Write ECU**: Flash modified tunes with safety verification
- **Compare ECU**: Diff between stock and modified tunes
- **Backup/Restore**: Automatic stock tune preservation
- **Direct Injection Support**: HPFP monitoring for GDI engines (LFX, LTG, etc.)

### 2. Transmission Tuning (TCM)
- Read transmission calibration
- Modify shift points and firmness
- Adjust torque converter lockup
- Optimize for performance or economy
- Support for 6L80/6L90, 8L90, 10L80, **6T70 (LFX Impala)**, etc.

### 3. Vehicle-Specific Support

#### LFX 3.6L V6 (2013 Chevrolet Impala)
- **Direct Injection**: HPFP & LPFP pressure monitoring
- **High Compression**: 12:1 compression knock analysis
- **Dual VVT**: Intake/exhaust cam position tracking
- **6T70 Trans**: FWD transmission tuning specific to Impala
- **LFX-Specific PIDs**: All 6 cylinder knock retard, injector duty, VVT tracking
- **Carbon Buildup**: Maintenance reminders for DI engines
- **Stage 1 Tuning**: Safe bolt-on tune template for LFX

### 3. Data Logging & Analysis
- Real-time sensor monitoring
- Wideband O2 integration
- Knock detection analysis
- Fuel trim evaluation
- Custom PID support

### 4. Tuning Workflows
- **Safe Stage 1**: Intake/exhaust basic tune
- **Stage 2**: Cam/heads advanced tuning
- **Forced Induction**: Turbo/supercharger specific
- **Flex Fuel**: E85 compatibility
- **Track Day**: Cooling and timing optimization

## Architecture

```
┌─────────────────────────────────────────┐
│         HP Tuners Master Agent          │
├─────────────────────────────────────────┤
│  ECU Module │ TCM Module │ Logger Module│
├─────────────────────────────────────────┤
│         OBD-II Interface Layer          │
│    (Bluetooth ELM327 / USB Adapter)     │
└─────────────────────────────────────────┘
```

## Core Components

### ECUController Class
```python
import obd
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class ECUParameters:
    vin: str
    calibration_id: str
    os_version: str
    fuel_type: str
    boost_enabled: bool = False
    flex_fuel_enabled: bool = False

@dataclass
class TuneData:
    spark_advance: Dict[str, float]  # RPM -> degrees
    fuel_mass: Dict[str, float]      # RPM -> mg
    airflow: Dict[str, float]        # MAF calibration
    torque_limits: Dict[str, int]    # Gear -> Nm

class ECUController:
    def __init__(self, port: str = None):
        self.connection = None
        self.port = port
        self.ecu_info: Optional[ECUParameters] = None
        self.current_tune: Optional[TuneData] = None
        self.data_log: List[Dict] = []
        
    def connect(self, protocol: str = "auto"):
        """Connect to OBD-II adapter"""
        if self.port:
            self.connection = obd.OBD(self.port, protocol=protocol)
        else:
            # Auto-detect Bluetooth/USB
            self.connection = obd.OBD()
        return self.connection.is_connected()
    
    def read_ecu_info(self) -> ECUParameters:
        """Read basic ECU identification"""
        vin = self.connection.query(obd.commands.VIN).value
        # Query mode 09 for calibration ID
        cal_id = self.connection.query(obd.commands.CALIBRATION_ID).value
        
        return ECUParameters(
            vin=str(vin),
            calibration_id=str(cal_id),
            os_version="Unknown",
            fuel_type="Gasoline"
        )
    
    def start_data_logging(self, pids: List[str], duration: int = 300):
        """Log specified PIDs for duration seconds"""
        self.data_log = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            entry = {"timestamp": time.time()}
            for pid in pids:
                cmd = getattr(obd.commands, pid.upper(), None)
                if cmd:
                    response = self.connection.query(cmd)
                    entry[pid] = response.value.magnitude if response.value else None
            self.data_log.append(entry)
            time.sleep(0.5)  # 2Hz logging rate
        
        return self.data_log
    
    def analyze_knock(self, log_data: List[Dict]) -> Dict:
        """Analyze knock sensor data from logs"""
        knock_events = [entry for entry in log_data 
                       if entry.get('KNOCK') and entry['KNOCK'] > 0]
        
        return {
            "total_events": len(knock_events),
            "max_knock": max((e['KNOCK'] for e in knock_events), default=0),
            "rpm_at_knock": [e.get('RPM') for e in knock_events],
            "recommendation": self._knock_recommendation(knock_events)
        }
    
    def _knock_recommendation(self, knock_events: List[Dict]) -> str:
        if len(knock_events) == 0:
            return "No knock detected - timing can be advanced 2-4 degrees"
        elif len(knock_events) < 5:
            return "Minor knock - reduce timing 1-2 degrees in affected RPM range"
        else:
            return "Significant knock - reduce timing 3-5 degrees, check fuel quality"
    
    def export_to_hp_tuners_format(self, output_path: Path):
        """Export current tune to HP Tuners compatible format"""
        # HP Tuners .hpt format structure
        tune_export = {
            "metadata": {
                "vin": self.ecu_info.vin if self.ecu_info else "Unknown",
                "calibration": self.ecu_info.calibration_id if self.ecu_info else "Unknown",
                "export_date": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "fuel": self.current_tune.fuel_mass if self.current_tune else {},
            "spark": self.current_tune.spark_advance if self.current_tune else {},
            "airflow": self.current_tune.airflow if self.current_tune else {},
        }
        
        with open(output_path, 'w') as f:
            json.dump(tune_export, f, indent=2)
```

### TransmissionController Class
```python
@dataclass
class TCMParameters:
    shift_points: Dict[str, Dict[str, int]]  # mode -> gear -> RPM
    line_pressure: int  # PSI
    converter_lockup: Dict[str, bool]  # gear -> enabled
    torque_management: int  # percentage

class TransmissionController:
    def __init__(self, ecu_controller: ECUController):
        self.ecu = ecu_controller
        self.tcm_data: Optional[TCMParameters] = None
    
    def read_tcm_calibration(self) -> TCMParameters:
        """Read transmission control module settings"""
        # OBD-II PID queries for TCM data
        # Note: Many TCM parameters require manufacturer-specific PIDs
        
        return TCMParameters(
            shift_points={
                "normal": {1: 5500, 2: 5800, 3: 6000, 4: 6200, 5: 6400, 6: 6800},
                "performance": {1: 6500, 2: 6800, 3: 7000, 4: 7200, 5: 7400, 6: 7600},
            },
            line_pressure=85,
            converter_lockup={2: False, 3: True, 4: True, 5: True, 6: True},
            torque_management=100
        )
    
    def create_performance_shift_profile(self, base_profile: Dict) -> Dict:
        """Generate performance-oriented shift points"""
        performance = {}
        for gear, rpm in base_profile.items():
            # Raise shift points by 800-1000 RPM
            performance[gear] = min(rpm + 800, 7500)
        return performance
    
    def optimize_for_drag_race(self) -> TCMParameters:
        """Maximum performance settings for drag racing"""
        return TCMParameters(
            shift_points={
                "launch": {1: 7000, 2: 7200, 3: 7400, 4: 7600}
            },
            line_pressure=120,  # Firmer shifts
            converter_lockup={2: False, 3: False, 4: True, 5: True, 6: False},
            torque_management=50  # Reduce torque management
        )
```

### TuneAnalyzer Class
```python
import pandas as pd
import numpy as np

class TuneAnalyzer:
    def __init__(self, log_data: List[Dict]):
        self.df = pd.DataFrame(log_data)
    
    def calculate_ve(self, rpm_range: tuple = (1000, 7000)) -> Dict:
        """Calculate volumetric efficiency from logs"""
        # VE = (Actual Airflow / Theoretical Airflow) * 100
        # Using MAF and RPM data
        
        filtered = self.df[
            (self.df['RPM'] >= rpm_range[0]) & 
            (self.df['RPM'] <= rpm_range[1])
        ]
        
        return {
            "avg_ve": filtered['MAF'].mean() if 'MAF' in filtered else 0,
            "peak_ve": filtered['MAF'].max() if 'MAF' in filtered else 0,
            "ve_by_rpm": filtered.groupby('RPM')['MAF'].mean().to_dict()
        }
    
    def find_max_power_rpm(self) -> int:
        """Estimate RPM of maximum power based on airflow"""
        if 'MAF' in self.df and 'RPM' in self.df:
            max_maf_idx = self.df['MAF'].idxmax()
            return int(self.df.loc[max_maf_idx, 'RPM'])
        return 0
    
    def fuel_trim_analysis(self) -> Dict:
        """Analyze fuel trims for tuning recommendations"""
        if 'SHORT_FUEL_TRIM' not in self.df:
            return {"error": "No fuel trim data available"}
        
        stft = self.df['SHORT_FUEL_TRIM']
        ltft = self.df.get('LONG_FUEL_TRIM', pd.Series([0] * len(stft)))
        
        return {
            "short_term_avg": stft.mean(),
            "long_term_avg": ltft.mean() if not isinstance(ltft, int) else 0,
            "fuel_correction_needed": abs(stft.mean()) > 5,
            "recommendation": self._fuel_trim_recommendation(stft.mean())
        }
    
    def _fuel_trim_recommendation(self, avg_trim: float) -> str:
        if abs(avg_trim) < 3:
            return "Fuel trims optimal - no adjustment needed"
        elif avg_trim > 5:
            return "Running lean - increase fuel mass 3-5%"
        elif avg_trim < -5:
            return "Running rich - decrease fuel mass 3-5%"
        else:
            return "Minor adjustment recommended"
```

## Tuning Workflows

### Stage 1: Basic Bolt-Ons
```python
def stage1_tune(base_tune: TuneData, mods: List[str]) -> TuneData:
    """
    Modifications: Cold air intake, cat-back exhaust, headers
    
    Changes:
    - MAF scaling adjustment (+8-12% airflow)
    - Spark advance +2-4 degrees in mid-range
    - WOT fuel enrichment -3%
    - Rev limiter +200-400 RPM (if safe)
    """
    tuned = TuneData(
        spark_advance={k: v + 2 for k, v in base_tune.spark_advance.items()},
        fuel_mass={k: v * 0.97 for k, v in base_tune.fuel_mass.items()},
        airflow={k: v * 1.10 for k, v in base_tune.airflow.items()},
        torque_limits=base_tune.torque_limits
    )
    return tuned
```

### Stage 2: Cam and Heads
```python
def stage2_tune(base_tune: TuneData, cam_specs: Dict) -> TuneData:
    """
    Modifications: Performance cam, ported heads, valvetrain
    
    Changes:
    - Idle airflow increase (larger cam)
    - VVT optimization for cam profile
    - Spark curve revised for new VE
    - Dynamic airflow tables updated
    - Startup and warm-up enrichment
    """
    tuned = TuneData(
        spark_advance=optimize_spark_for_cam(base_tune.spark_advance, cam_specs),
        fuel_mass=adjust_fuel_for_ve_changes(base_tune.fuel_mass, cam_specs),
        airflow=recalculate_maf_with_new_ve(base_tune.airflow, cam_specs),
        torque_limits={k: int(v * 1.15) for k, v in base_tune.torque_limits.items()}
    )
    return tuned
```

### Forced Induction
```python
def forced_induction_tune(base_tune: TuneData, boost_pressure: float) -> TuneData:
    """
    Modifications: Turbo or supercharger kit
    
    Critical Safety:
    - Fuel system capacity verification
    - Spark retard under boost
    - Boost cut limits
    - Knock sensor sensitivity increase
    """
    psi = boost_pressure
    
    tuned = TuneData(
        spark_advance=retard_spark_under_boost(base_tune.spark_advance, psi),
        fuel_mass=enrich_fuel_for_boost(base_tune.fuel_mass, psi),
        airflow=scale_maf_for_boost(base_tune.airflow, psi),
        torque_limits={k: min(int(v * (1 + psi/14.7)), 800) for k, v in base_tune.torque_limits.items()}
    )
    
    # Safety: Enable boost cut if not present
    # Enable intercooler fan control
    # Increase injector duty cycle limits
    
    return tuned
```

## Safety Systems

### Pre-Flash Checklist
```python
class SafetyValidator:
    @staticmethod
    def validate_flash(tune: TuneData, ecu_info: ECUParameters) -> Dict:
        checks = {
            "stock_backup": False,
            "fuel_system_ok": False,
            "knk_sensor_active": False,
            "temperature_safe": False,
            "battery_voltage_ok": False
        }
        
        # Verify stock backup exists
        stock_path = Path(f"backups/{ecu_info.vin}_stock.json")
        checks["stock_backup"] = stock_path.exists()
        
        # Check fuel trims
        if tune.fuel_mass:
            max_fuel = max(tune.fuel_mass.values())
            checks["fuel_system_ok"] = max_fuel < 150  # mg/cyl limit
        
        # Recommendations
        recommendations = []
        if not checks["stock_backup"]:
            recommendations.append("BACKUP STOCK TUNE BEFORE FLASHING")
        if not checks["fuel_system_ok"]:
            recommendations.append("FUEL DEMAND EXCEEDS INJECTOR CAPACITY")
        
        return {
            "safe_to_flash": all(checks.values()),
            "checks": checks,
            "recommendations": recommendations
        }
```

## Data Logging PIDs

### Essential PIDs
- **RPM**: Engine speed
- **SPEED**: Vehicle speed
- **MAF**: Mass airflow sensor
- **O2_B1S1**: Bank 1 upstream O2
- **O2_B2S1**: Bank 2 upstream O2
- **SHORT_FUEL_TRIM**: STFT
- **LONG_FUEL_TRIM**: LTFT
- **SPARK_ADV**: Spark advance
- **KNOCK**: Knock retard
- **ENGINE_LOAD**: Calculated load
- **THROTTLE_POS**: Throttle position
- **COOLANT_TEMP**: ECT
- **INTAKE_TEMP**: IAT
- **TIMING_ADV**: Timing advance

### Wideband Integration
```python
def integrate_wideband(wideband_port: str, ecu: ECUController):
    """Integrate external wideband O2 sensor"""
    # Many tuners use external wideband for more accurate AFR
    # This requires reading from serial port or analog input
    import serial
    
    wb = serial.Serial(wideband_port, 9600, timeout=1)
    
    while ecu.connection.is_connected():
        line = wb.readline().decode().strip()
        if line:
            afr = float(line)
            # Log alongside ECU data
            ecu.data_log.append({
                "timestamp": time.time(),
                "wideband_afr": afr,
                "target_afr": 12.8 if wideband_condition else 14.7
            })
```

## HP Tuners Integration

### Export to HPT Format
```python
class HPTunersExporter:
    def export_tunefile(self, tune: TuneData, output_path: Path):
        """Export to HP Tuners .tun file format"""
        # Structure matches HP Tuners Editor tables
        hpt_structure = {
            "Header": {
                "Version": "2.0",
                "Vehicle": self.get_vehicle_info(),
                "OS": self.get_os_info()
            },
            "Tables": {
                "Fuel": {
                    "PE": tune.fuel_mass,
                    "Base": tune.airflow
                },
                "Spark": {
                    "Main": tune.spark_advance,
                    "KR": {}  # Knock retard table
                },
                "Trans": {
                    "Shift": self.tcm.shift_points if self.tcm else {},
                    "TCC": self.tcm.converter_lockup if self.tcm else {}
                }
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(hpt_structure, f)
```

## Usage Example

```python
# Initialize controller
ecu = ECUController(port="/dev/rfcomm0")  # Bluetooth OBD-II
if ecu.connect():
    print("Connected to vehicle")
    
    # Read ECU info
    info = ecu.read_ecu_info()
    print(f"VIN: {info.vin}")
    print(f"Calibration: {info.calibration_id}")
    
    # Start logging for baseline
    print("Logging baseline data...")
    log = ecu.start_data_logging(
        pids=["RPM", "MAF", "O2_B1S1", "SHORT_FUEL_TRIM", "KNOCK"],
        duration=600  # 10 minutes
    )
    
    # Analyze
    analyzer = TuneAnalyzer(log)
    knock_analysis = ecu.analyze_knock(log)
    fuel_analysis = analyzer.fuel_trim_analysis()
    
    print(f"Knock events: {knock_analysis['total_events']}")
    print(f"Fuel trim recommendation: {fuel_analysis['recommendation']}")
    
    # Create tune
    base = ecu.current_tune or load_stock_tune()
    stage1 = stage1_tune(base, mods=["intake", "exhaust"])
    
    # Safety check
    safety = SafetyValidator.validate_flash(stage1, info)
    if safety["safe_to_flash"]:
        print("Safe to flash tune")
    else:
        print("Issues found:", safety["recommendations"])
```

## Installation Requirements

```bash
# Python dependencies
pip install python-obd python-can pandas numpy pyserial

# System dependencies (Linux)
# For Bluetooth OBD-II adapters
sudo apt install bluetooth bluez blueman

# For USB serial adapters
sudo usermod -a -G dialout $USER

# For CAN bus (if using CAN sniffer)
# Install can-utils package
```

## Best Practices

### 1. Always Log First
- Log 10-15 minutes of varied driving
- Include idle, cruise, WOT acceleration
- Note environmental conditions

### 2. Make Small Changes
- Never change more than one parameter at a time
- Document every change with before/after logs
- Test each change before adding more

### 3. Safety First
- Backup stock tune before any changes
- Keep knock sensor active and sensitive
- Monitor coolant temps closely
- Have wideband O2 for boosted applications

### 4. Transmission Considerations
- Don't exceed torque converter limits
- Adjust line pressure gradually
- Test shift quality at various throttle positions
- Consider daily drivability vs. track performance

## Common Issues

### Lean Condition
- Check fuel trims > +10%
- Monitor WOT AFR (target 11.5-12.5 for boosted)
- Increase fuel mass or decrease airflow

### Knock
- Pull timing 2-4 degrees at affected RPM
- Check fuel quality (93 vs 91 octane)
- Monitor IAT (hot air causes knock)

### Rough Idle
- Increase airflow at idle (MAF or dynamic)
- Adjust idle spark advance
- Check for vacuum leaks

### Transmission Slipping
- Increase line pressure
- Check fluid level and condition
- Don't exceed clutch pack torque limits

## Vehicle-Specific Resources

### LFX 3.6L V6 (2013 Impala) Support Files

**Profile Template**: `templates/lfx_impala_2013_profile.json`
- Complete LFX engine specifications
- Stock table values (fuel pressure, spark, VVT)
- LFX-specific PID definitions
- Stage 1 tuning recommendations
- Known issues (carbon buildup, timing chain, HPFP)

**Tuning Guide**: `references/lfx_tuning_guide.md`
- Direct injection fuel system tuning
- High compression (12:1) considerations
- VVT optimization strategies
- 6T70 transmission tuning
- Carbon buildup maintenance
- Data logging strategy for LFX

**LFX Controller**: `scripts/lfx_impala_controller.py`
- LFX-specific PID logging list
- HPFP & injector duty analysis
- 6-cylinder knock analysis
- VVT tracking verification
- Stage 1 tune generator
- Maintenance checklist by mileage

### Using LFX-Specific Features

```python
from hp_tuners_agent import HPTunersAgent
from lfx_impala_controller import LFXImpalaController

# Initialize main agent
agent = HPTunersAgent()
agent.initialize()

# Add LFX-specific controller
lfx = LFXImpalaController(agent.ecu)

# Get LFX-specific PIDs
pids = lfx.get_lfx_logging_pids()

# Log with LFX-specific monitoring
log_data = agent.ecu.start_data_logging(pids, duration=600)

# LFX-specific analysis
fuel_analysis = lfx.analyze_lfx_fuel_system(log_data)
knock_analysis = lfx.analyze_lfx_knock(log_data)
vvt_analysis = lfx.analyze_vvt_operation(log_data)

# Generate LFX-specific Stage 1 tune
tune = lfx.generate_stage1_lfx_tune(octane_rating=93)

# Pre-tune maintenance check
maintenance_items = lfx.check_maintenance_items(mileage=85000)
for item in maintenance_items:
    print(item)
```

## Resources

- HP Tuners Forums: https://www.hptuners.com/forums/
  - LFX Section: http://www.hptuners.com/forum/forumdisplay.php?fid=123
- EFI University: https://www.efiuniversity.com/
- Tuning School: https://www.thetuningschool.com/
- OBD-II PID Database: https://en.wikipedia.org/wiki/OBD-II_PIDs
- Impala Forums: www.impalaforums.com
- LFX Carbon Buildup Info: Search "LFX walnut blasting"

## Disclaimer

ECU tuning modifies critical vehicle safety systems. Improper tuning can cause:
- Engine damage or failure
- Transmission damage
- Loss of vehicle control
- Voided warranty

Always:
- Start with conservative changes
- Monitor engine parameters continuously
- Have mechanical knowledge or professional assistance
- Follow manufacturer guidelines and local laws