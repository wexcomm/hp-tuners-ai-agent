#!/usr/bin/env python3
"""
HP Tuners Table Template Generator
Creates properly formatted tuning tables for various modifications
"""

import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TableAxis:
    """Table axis definition"""
    name: str
    units: str
    values: List[float]
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "units": self.units,
            "values": self.values,
            "description": self.description
        }


@dataclass
class TuneTable:
    """Complete tuning table"""
    name: str
    category: str
    description: str
    row_axis: TableAxis
    col_axis: Optional[TableAxis]  # None for 2D tables
    data: List[List[float]]
    units: str
    min_safe: float
    max_safe: float
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "row_axis": self.row_axis.to_dict(),
            "col_axis": self.col_axis.to_dict() if self.col_axis else None,
            "data": self.data,
            "units": self.units,
            "safety_limits": {"min": self.min_safe, "max": self.max_safe},
            "warnings": self.warnings
        }
        
    def modify(self, modifier: Callable[[float, float, float], float]) -> 'TuneTable':
        """Apply a modification function to all cells"""
        new_data = []
        for row_idx, row in enumerate(self.data):
            new_row = []
            for col_idx, value in enumerate(row):
                row_val = self.row_axis.values[row_idx]
                col_val = self.col_axis.values[col_idx] if self.col_axis else 0
                new_row.append(modifier(value, row_val, col_val))
            new_data.append(new_row)
        
        # Create new table with modified data
        new_table = TuneTable(
            name=f"{self.name}_modified",
            category=self.category,
            description=f"Modified: {self.description}",
            row_axis=self.row_axis,
            col_axis=self.col_axis,
            data=new_data,
            units=self.units,
            min_safe=self.min_safe,
            max_safe=self.max_safe,
            warnings=self.warnings.copy()
        )
        return new_table
        
    def validate(self) -> List[str]:
        """Validate table values are within safe limits"""
        issues = []
        flat_data = [v for row in self.data for v in row]
        
        actual_min = min(flat_data)
        actual_max = max(flat_data)
        
        if actual_min < self.min_safe:
            issues.append(f"WARNING: Values below minimum safe limit ({actual_min:.2f} < {self.min_safe})")
        if actual_max > self.max_safe:
            issues.append(f"CRITICAL: Values exceed maximum safe limit ({actual_max:.2f} > {self.max_safe})")
            
        return issues


class SparkTableGenerator:
    """Generate spark advance tables"""
    
    # Base spark curves for common engines (degrees BTDC at 100% load)
    BASE_CURVES = {
        "gm_lfx_stock": {
            "description": "GM LFX 3.6L V6 stock calibration",
            "octane": 87,
            "curve": {
                800: 15, 1000: 18, 1500: 22, 2000: 26, 2500: 28,
                3000: 30, 3500: 30, 4000: 28, 4500: 26, 5000: 24,
                5500: 22, 6000: 20, 6500: 18
            }
        },
        "gm_lfx_93": {
            "description": "GM LFX 3.6L V6 optimized for 93 octane",
            "octane": 93,
            "curve": {
                800: 18, 1000: 22, 1500: 26, 2000: 30, 2500: 32,
                3000: 34, 3500: 34, 4000: 32, 4500: 30, 5000: 28,
                5500: 26, 6000: 24, 6500: 22
            }
        },
        "gm_ls3_stock": {
            "description": "GM LS3 6.2L V8 stock calibration",
            "octane": 91,
            "curve": {
                800: 18, 1000: 22, 1500: 26, 2000: 30, 2500: 32,
                3000: 34, 3500: 34, 4000: 32, 4500: 30, 5000: 28,
                5500: 26, 6000: 24, 6500: 22, 7000: 20
            }
        }
    }
    
    @staticmethod
    def generate_main_spark_table(
        base_curve: str = "gm_lfx_stock",
        rpm_range: Tuple[int, int] = (800, 7000),
        load_breakpoints: List[int] = None,
        octane_rating: int = 87
    ) -> TuneTable:
        """Generate main spark advance (MBT) table"""
        
        if load_breakpoints is None:
            load_breakpoints = [20, 40, 60, 80, 100]
            
        base = SparkTableGenerator.BASE_CURVES.get(base_curve, 
                                                   SparkTableGenerator.BASE_CURVES["gm_lfx_stock"])
        
        # Extract RPM points from base curve or generate
        base_rpms = sorted(base["curve"].keys())
        
        # Generate row (load) and column (RPM) axes
        row_axis = TableAxis(
            name="Engine Load",
            units="%",
            values=[float(l) for l in load_breakpoints],
            description="Calculated engine load"
        )
        
        col_axis = TableAxis(
            name="Engine Speed",
            units="RPM",
            values=[float(r) for r in base_rpms],
            description="Engine RPM"
        )
        
        # Generate data matrix
        data = []
        for load in load_breakpoints:
            row = []
            for rpm in base_rpms:
                base_timing = base["curve"][rpm]
                
                # Adjust for load - less timing at higher loads
                load_factor = load / 100.0
                if load <= 60:
                    timing = base_timing
                elif load <= 80:
                    timing = base_timing - 2 * (load_factor - 0.6)
                else:
                    timing = base_timing - 2 * 0.2 - 4 * (load_factor - 0.8)
                    
                # Adjust for octane if different from base
                octane_diff = octane_rating - base["octane"]
                if octane_diff > 0:
                    timing += octane_diff * 0.5  # +0.5° per octane point
                elif octane_diff < 0:
                    timing += octane_diff * 1.0  # -1° per octane point (safer)
                    
                row.append(round(timing, 1))
            data.append(row)
            
        warnings = []
        if octane_rating < 91:
            warnings.append("Low octane - monitor knock closely, reduce timing if needed")
        if max(max(row) for row in data) > 40:
            warnings.append("High timing values - verify with knock monitoring")
            
        return TuneTable(
            name="Main Spark Advance",
            category="Engine - Spark",
            description=f"Primary ignition timing table ({octane_rating} octane)",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="°BTDC",
            min_safe=-10,
            max_safe=45,
            warnings=warnings
        )
        
    @staticmethod
    def generate_knock_retard_table(
        rpm_range: Tuple[int, int] = (800, 7000),
        load_breakpoints: List[int] = None
    ) -> TuneTable:
        """Generate knock retard limits table"""
        
        if load_breakpoints is None:
            load_breakpoints = [20, 40, 60, 80, 100]
            
        rpms = list(range(rpm_range[0], rpm_range[1] + 1, 500))
        
        row_axis = TableAxis("Engine Load", "%", [float(l) for l in load_breakpoints])
        col_axis = TableAxis("Engine Speed", "RPM", [float(r) for r in rpms])
        
        # Knock retard limits - higher at high load/RPM
        data = []
        for load in load_breakpoints:
            row = []
            for rpm in rpms:
                if load < 60 and rpm < 4000:
                    limit = 8.0
                elif load < 80:
                    limit = 10.0
                else:
                    limit = 12.0
                row.append(limit)
            data.append(row)
            
        return TuneTable(
            name="Knock Retard Limit",
            category="Engine - Spark",
            description="Maximum timing retard allowed per knock event",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="°",
            min_safe=0,
            max_safe=15,
            warnings=["Higher limits = more timing pulled = safer but less power"]
        )


class FuelTableGenerator:
    """Generate fuel mass and related tables"""
    
    @staticmethod
    def generate_base_fuel_mass(
        displacement: float = 3.6,  # Liters
        injector_size: float = 45,   # lbs/hr
        num_cylinders: int = 6
    ) -> TuneTable:
        """Generate base fuel mass table"""
        
        rpm_breakpoints = [800, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 
                         4500, 5000, 5500, 6000, 6500, 7000]
        load_breakpoints = [20, 40, 60, 80, 100]
        
        row_axis = TableAxis("Engine Load", "%", [float(l) for l in load_breakpoints])
        col_axis = TableAxis("Engine Speed", "RPM", [float(r) for r in rpm_breakpoints])
        
        # Calculate approximate fuel mass based on displacement and airflow
        # This is simplified - real tables are much more complex
        data = []
        for load in load_breakpoints:
            row = []
            for rpm in rpm_breakpoints:
                # Rough estimate: base fuel increases with load and RPM
                base_mass = 30  # mg/cyl at idle
                
                # RPM factor
                rpm_factor = 1 + (rpm - 800) / 7000 * 2.5
                
                # Load factor
                load_factor = load / 100.0
                
                # Calculate
                fuel_mass = base_mass * rpm_factor * load_factor
                
                # Enrichment at high load
                if load > 80:
                    fuel_mass *= 1.1
                    
                row.append(round(fuel_mass, 1))
            data.append(row)
            
        return TuneTable(
            name="Base Fuel Mass",
            category="Engine - Fuel",
            description=f"Base fuel injector pulse width ({displacement}L V{num_cylinders})",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="mg/cyl",
            min_safe=10,
            max_safe=150,
            warnings=["Verify with wideband O2 sensor", f"Max injector duty cycle: check <85%"]
        )
        
    @staticmethod
    def generate_power_enrichment(octane: int = 93) -> TuneTable:
        """Generate power enrichment (WOT) lambda targets"""
        
        rpms = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]
        
        row_axis = TableAxis("Commanded", "", [1.0])
        col_axis = TableAxis("Engine Speed", "RPM", [float(r) for r in rpms])
        
        # Lambda targets: richer at higher RPM for cooling
        # 0.85 lambda = ~12.4:1 AFR (gasoline)
        data = []
        row = []
        for rpm in rpms:
            if rpm < 3000:
                lambda_target = 0.88  # ~12.9:1
            elif rpm < 5000:
                lambda_target = 0.86  # ~12.6:1
            else:
                lambda_target = 0.85  # ~12.4:1 (more cooling)
            row.append(lambda_target)
        data.append(row)
        
        warnings = []
        if octane >= 93:
            warnings.append("93+ octane - can lean to 0.88-0.90 for more power")
        else:
            warnings.append("Lower octane - keep rich 0.85-0.87 for cooling")
            
        return TuneTable(
            name="Power Enrichment",
            category="Engine - Fuel",
            description=f"WOT lambda targets ({octane} octane)",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="Lambda",
            min_safe=0.75,
            max_safe=1.0,
            warnings=warnings
        )


class MAFCalibrationGenerator:
    """Generate MAF calibration curves"""
    
    @staticmethod
    def generate_maf_calibration(
        tube_diameter_mm: float = 85,  # Stock LFX
        calibration_type: str = "stock"
    ) -> TuneTable:
        """Generate MAF voltage to airflow calibration"""
        
        # Standard voltage breakpoints
        voltages = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        
        row_axis = TableAxis("MAF Voltage", "V", voltages)
        
        # Calculate flow based on tube diameter
        # Flow ~ (diameter/85)^2 * reference_flow
        scale_factor = (tube_diameter_mm / 85.0) ** 2
        
        # Stock LFX MAF curve (approximate)
        stock_flows = [0, 5, 15, 30, 55, 85, 120, 160, 205, 255, 310]
        
        if calibration_type == "intake_modified":
            # Cold air intake typically flows 8-12% more
            scale_factor *= 1.10
            description = f"MAF calibration for {tube_diameter_mm}mm intake (+10% flow)"
        elif calibration_type == "turbo":
            # Turbo needs much higher range
            scale_factor *= 2.5
            description = f"MAF calibration for {tube_diameter_mm}mm turbo setup"
        else:
            description = f"Stock MAF calibration for {tube_diameter_mm}mm tube"
            
        flows = [f * scale_factor for f in stock_flows]
        
        data = [[f] for f in flows]
        
        return TuneTable(
            name="MAF Calibration",
            category="Engine - Airflow",
            description=description,
            row_axis=row_axis,
            col_axis=None,
            data=data,
            units="g/s",
            min_safe=0,
            max_safe=500,
            warnings=["Always verify with wideband O2 after scaling"]
        )


class VETableGenerator:
    """Generate Volumetric Efficiency tables"""
    
    @staticmethod
    def generate_ve_table(
        engine: str = "lfx_stock",
        rpm_range: Tuple[int, int] = (800, 7000),
        map_breakpoints: List[int] = None
    ) -> TuneTable:
        """Generate VE (Speed Density) table"""
        
        if map_breakpoints is None:
            map_breakpoints = [40, 60, 80, 100]
            
        rpms = [800, 1200, 1600, 2000, 2400, 2800, 3200, 3600, 4000, 
               4500, 5000, 5500, 6000, 6500, 7000]
        
        row_axis = TableAxis("MAP", "kPa", [float(m) for m in map_breakpoints])
        col_axis = TableAxis("Engine Speed", "RPM", [float(r) for r in rpms])
        
        # Typical VE curves - peak around torque peak
        # LFX peaks around 4000-5000 RPM
        data = []
        for map_val in map_breakpoints:
            row = []
            for rpm in rpms:
                # Base VE increases with RPM to peak, then drops
                if rpm < 4000:
                    base_ve = 75 + (rpm - 800) / 3200 * 20  # 75% to 95%
                elif rpm < 5500:
                    base_ve = 95  # Peak
                else:
                    base_ve = 95 - (rpm - 5500) / 1500 * 10  # Drop to 85%
                    
                # MAP correction - higher MAP = higher VE
                map_factor = map_val / 100.0
                
                ve = base_ve * map_factor
                row.append(round(ve, 1))
            data.append(row)
            
        return TuneTable(
            name="Volumetric Efficiency",
            category="Engine - Airflow",
            description=f"VE table for {engine}",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="%",
            min_safe=50,
            max_safe=110,
            warnings=["Must be accurate for speed density operation", "Verify with MAF for calibration"]
        )


class TransmissionTableGenerator:
    """Generate transmission tuning tables"""
    
    @staticmethod
    def generate_shift_table(
        trans_type: str = "6t70",
        style: str = "normal",
        rpm_increase: int = 0
    ) -> TuneTable:
        """Generate shift point table"""
        
        tps_points = [0, 10, 25, 50, 75, 100]
        
        row_axis = TableAxis("Throttle Position", "%", [float(t) for t in tps_points])
        
        # Define shift RPMs by transmission and style
        shift_configs = {
            "6t70": {
                "normal": {
                    "1-2": 5500, "2-3": 5700, "3-4": 5900, 
                    "4-5": 6000, "5-6": 6100
                },
                "sport": {
                    "1-2": 6200, "2-3": 6400, "3-4": 6600,
                    "4-5": 6800, "5-6": 7000
                },
                "conservative": {
                    "1-2": 5000, "2-3": 5200, "3-4": 5400,
                    "4-5": 5500, "5-6": 5600
                }
            },
            "6l80": {
                "normal": {
                    "1-2": 5800, "2-3": 6000, "3-4": 6200,
                    "4-5": 6400, "5-6": 6600
                },
                "sport": {
                    "1-2": 6500, "2-3": 6700, "3-4": 6900,
                    "4-5": 7000, "5-6": 7200
                }
            }
        }
        
        config = shift_configs.get(trans_type, shift_configs["6t70"])
        base_shifts = config.get(style, config["normal"])
        
        # Create columns for each shift
        gears = ["1-2", "2-3", "3-4", "4-5", "5-6"]
        col_axis = TableAxis("Shift", "", gears)
        
        data = []
        for tps in tps_points:
            row = []
            for gear in gears:
                base_rpm = base_shifts[gear]
                
                # Adjust based on throttle
                if tps < 25:
                    # Light throttle - shift much earlier
                    rpm = base_rpm - 1500 + (tps * 20)
                elif tps < 50:
                    # Moderate throttle
                    rpm = base_rpm - 800 + ((tps - 25) * 20)
                else:
                    # Heavy throttle - use base or higher
                    rpm = base_rpm + ((tps - 50) * 10)
                    
                # Apply global increase
                rpm += rpm_increase
                
                # Safety cap
                rpm = min(rpm, 7200)
                
                row.append(float(rpm))
            data.append(row)
            
        return TuneTable(
            name=f"{style.title()} Shift Speeds",
            category="Transmission - Shift",
            description=f"Upshift RPMs for {trans_type} - {style} mode",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="RPM",
            min_safe=3000,
            max_safe=7500,
            warnings=["Stay below mechanical redline", "Consider torque converter slip"]
        )
        
    @staticmethod
    def generate_line_pressure_table(trans_type: str = "6t70") -> TuneTable:
        """Generate transmission line pressure table"""
        
        loads = [20, 40, 60, 80, 100]
        gears = ["1", "2", "3", "4", "5", "6", "R"]
        
        row_axis = TableAxis("Engine Load", "%", [float(l) for l in loads])
        col_axis = TableAxis("Gear", "", gears)
        
        # Base pressure around 85-90 PSI stock
        base_pressure = 85
        
        data = []
        for load in loads:
            row = []
            for gear in gears:
                # Pressure increases with load
                pressure = base_pressure + (load - 20) * 0.3
                
                # Reverse gets more pressure
                if gear == "R":
                    pressure += 10
                    
                row.append(round(pressure, 1))
            data.append(row)
            
        return TuneTable(
            name="Line Pressure",
            category="Transmission - Pressure",
            description=f"Base line pressure for {trans_type}",
            row_axis=row_axis,
            col_axis=col_axis,
            data=data,
            units="PSI",
            min_safe=70,
            max_safe=130,
            warnings=["Too low = slipping/burn clutches", "Too high = harsh shifts/pump wear"]
        )


class CompleteTuneBuilder:
    """Build complete tune packages for common modifications"""
    
    @staticmethod
    def build_stage1_tune(
        vehicle: str = "lfx_impala",
        octane: int = 93,
        mods: List[str] = None
    ) -> Dict[str, TuneTable]:
        """Build Stage 1 tune (CAI, exhaust)"""
        
        if mods is None:
            mods = ["intake", "exhaust"]
            
        tables = {}
        
        # Spark - optimized for octane
        spark = SparkTableGenerator.generate_main_spark_table(
            base_curve="gm_lfx_stock",
            octane_rating=octane
        )
        tables["spark_main"] = spark
        
        # Knock limits
        tables["knock_limit"] = SparkTableGenerator.generate_knock_retard_table()
        
        # MAF - scale for intake if present
        if "intake" in mods:
            maf = MAFCalibrationGenerator.generate_maf_calibration(
                calibration_type="intake_modified"
            )
        else:
            maf = MAFCalibrationGenerator.generate_maf_calibration()
        tables["maf"] = maf
        
        # Fuel
        tables["fuel_mass"] = FuelTableGenerator.generate_base_fuel_mass()
        tables["power_enrichment"] = FuelTableGenerator.generate_power_enrichment(octane)
        
        # VE
        tables["ve"] = VETableGenerator.generate_ve_table()
        
        # Transmission - raise shift points slightly
        tables["shift_normal"] = TransmissionTableGenerator.generate_shift_table(
            style="normal", rpm_increase=200
        )
        tables["shift_sport"] = TransmissionTableGenerator.generate_shift_table(
            style="sport", rpm_increase=300
        )
        tables["line_pressure"] = TransmissionTableGenerator.generate_line_pressure_table()
        
        return tables
        
    @staticmethod
    def export_tune_package(tables: Dict[str, TuneTable], output_dir: Path):
        """Export complete tune to directory"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported = []
        for name, table in tables.items():
            # Validate first
            issues = table.validate()
            if issues:
                logger.warning(f"Validation issues in {name}:")
                for issue in issues:
                    logger.warning(f"  {issue}")
                    
            # Export as JSON
            filepath = output_dir / f"{name}.json"
            with open(filepath, 'w') as f:
                json.dump(table.to_dict(), f, indent=2)
            exported.append(filepath)
            
            # Export as CSV
            csv_path = output_dir / f"{name}.csv"
            with open(csv_path, 'w') as f:
                # Header
                if table.col_axis:
                    f.write(f"{table.row_axis.name}\\{table.col_axis.name},")
                    f.write(",".join([str(v) for v in table.col_axis.values]) + "\n")
                else:
                    f.write(f"{table.row_axis.name},{table.units}\n")
                    
                # Data
                for i, row in enumerate(table.data):
                    f.write(f"{table.row_axis.values[i]},")
                    f.write(",".join([str(v) for v in row]) + "\n")
                    
        return exported


if __name__ == "__main__":
    # Example: Generate Stage 1 tune
    print("Generating Stage 1 LFX tune...")
    
    tune = CompleteTuneBuilder.build_stage1_tune(
        vehicle="lfx_impala",
        octane=93,
        mods=["intake", "exhaust"]
    )
    
    print(f"\nGenerated {len(tune)} tables:")
    for name, table in tune.items():
        issues = table.validate()
        status = "✓" if not issues else "⚠"
        print(f"  {status} {name}: {table.description}")
        if issues:
            for issue in issues:
                print(f"      {issue}")
                
    # Export example
    # CompleteTuneBuilder.export_tune_package(tune, "./stage1_tune")
