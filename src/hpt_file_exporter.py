#!/usr/bin/env python3
"""
HP Tuners Native File Format Exporter
Generates .HPT compatible tune files that can be opened directly in VCM Editor
"""

import json
import struct
import zlib
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class HPTTable:
    """Represents a single tuning table"""
    name: str
    category: str  # Engine, Transmission, Fuel, Spark, etc.
    row_axis: List[float]  # RPM, Load, etc.
    col_axis: List[float]  # Secondary axis (if 3D)
    data: List[List[float]]  # 2D table values
    units: str
    description: str
    min_value: float
    max_value: float
    
    def to_hpt_format(self) -> Dict:
        """Convert to HP Tuners table structure"""
        return {
            "TableName": self.name,
            "Category": self.category,
            "RowAxis": {
                "Values": self.row_axis,
                "Units": self._get_axis_units(self.name, 'row')
            },
            "ColAxis": {
                "Values": self.col_axis,
                "Units": self._get_axis_units(self.name, 'col')
            } if self.col_axis else None,
            "Data": self.data,
            "Units": self.units,
            "Description": self.description,
            "Min": self.min_value,
            "Max": self.max_value
        }
    
    def _get_axis_units(self, table_name: str, axis: str) -> str:
        """Get appropriate axis units based on table type"""
        if 'RPM' in table_name.upper():
            return "RPM"
        if axis == 'row':
            if 'LOAD' in table_name.upper() or 'MASS' in table_name.upper():
                return "mg/cyl"
            if 'TPS' in table_name.upper():
                return "%"
            if 'MAP' in table_name.upper() or 'PRESSURE' in table_name.upper():
                return "kPa"
        return ""


class HPTTuneFile:
    """
    HP Tuners .HPT File Generator
    Creates files compatible with VCM Editor 5.x
    """
    
    # Supported vehicle platforms
    PLATFORMS = {
        "GM_E38": {"ecm": "E38", "tcm": "T42", "description": "GM Gen IV V8"},
        "GM_E67": {"ecm": "E67", "tcm": "T42", "description": "GM Gen IV V8 (Corvette)"},
        "GM_E41": {"ecm": "E41", "tcm": "T43", "description": "GM Gen V V8"},
        "GM_E39": {"ecm": "E39", "tcm": "T43", "description": "GM Gen V V8 (Truck)"},
        "GM_E37": {"ecm": "E37", "tcm": "T42", "description": "GM LFX/LFX 3.6L V6"},
        "GM_E78": {"ecm": "E78", "tcm": "T76", "description": "GM 2.0T/2.5L"},
    }
    
    def __init__(self, vin: str, calibration_id: str, platform: str = "GM_E37"):
        self.vin = vin
        self.calibration_id = calibration_id
        self.platform = platform
        self.tables: Dict[str, HPTTable] = {}
        self.metadata = {
            "CreatedBy": "HP Tuners AI Agent",
            "Version": "1.0",
            "Date": datetime.now().isoformat(),
            "Platform": platform,
            "ECM": self.PLATFORMS.get(platform, {}).get("ecm", "Unknown"),
            "TCM": self.PLATFORMS.get(platform, {}).get("tcm", "Unknown")
        }
        
    def add_table(self, table: HPTTable):
        """Add a tuning table"""
        self.tables[table.name] = table
        logger.info(f"Added table: {table.name}")
        
    def create_spark_table(self, spark_data: Dict[str, Dict[str, float]], 
                           name: str = "Spark Advance") -> HPTTable:
        """Create main spark advance table"""
        # Extract axes
        rpm_values = sorted([int(k) for k in list(spark_data.values())[0].keys()])
        load_values = sorted([int(k) for k in spark_data.keys()])
        
        # Build data matrix
        data = []
        for load in load_values:
            row = []
            load_str = str(load)
            for rpm in rpm_values:
                rpm_str = str(rpm)
                value = spark_data.get(load_str, {}).get(rpm_str, 20.0)
                row.append(float(value))
            data.append(row)
            
        return HPTTable(
            name=name,
            category="Engine - Spark",
            row_axis=[float(r) for r in rpm_values],
            col_axis=[float(l) for l in load_values],
            data=data,
            units="Degrees",
            description="Main spark advance table (MBT)",
            min_value=-20.0,
            max_value=60.0
        )
        
    def create_fuel_mass_table(self, fuel_data: Dict[str, Dict[str, float]],
                                name: str = "Base Fuel Mass") -> HPTTable:
        """Create base fuel mass table"""
        rpm_values = sorted([int(k) for k in list(fuel_data.values())[0].keys()])
        load_values = sorted([int(k) for k in fuel_data.keys()])
        
        data = []
        for load in load_values:
            row = []
            load_str = str(load)
            for rpm in rpm_values:
                rpm_str = str(rpm)
                value = fuel_data.get(load_str, {}).get(rpm_str, 50.0)
                row.append(float(value))
            data.append(row)
            
        return HPTTable(
            name=name,
            category="Engine - Fuel",
            row_axis=[float(r) for r in rpm_values],
            col_axis=[float(l) for l in load_values],
            data=data,
            units="mg/cyl",
            description="Base fuel injector pulse width",
            min_value=0.0,
            max_value=200.0
        )
        
    def create_maf_calibration(self, voltage_flow_points: List[Tuple[float, float]]) -> HPTTable:
        """Create MAF calibration curve"""
        voltages = [p[0] for p in voltage_flow_points]
        flows = [[p[1]] for p in voltage_flow_points]
        
        return HPTTable(
            name="MAF Calibration",
            category="Engine - Airflow",
            row_axis=voltages,
            col_axis=[],
            data=flows,
            units="g/s",
            description="MAF voltage to airflow conversion",
            min_value=0.0,
            max_value=500.0
        )
        
    def create_shift_table(self, shift_points: Dict[str, Dict[str, int]],
                           name: str = "Normal Shift Speeds") -> HPTTable:
        """Create transmission shift table"""
        gears = sorted(shift_points.keys())
        tps_values = sorted([int(k) for k in list(shift_points.values())[0].keys()])
        
        data = []
        for gear in gears:
            row = []
            for tps in tps_values:
                value = shift_points.get(gear, {}).get(str(tps), 5000)
                row.append(float(value))
            data.append(row)
            
        return HPTTable(
            name=name,
            category="Transmission - Shift",
            row_axis=[float(t) for t in tps_values],
            col_axis=[],
            data=data,
            units="RPM",
            description="Upshift RPM vs TPS",
            min_value=1000.0,
            max_value=8000.0
        )
        
    def create_torque_limit_table(self, limits: Dict[str, int]) -> HPTTable:
        """Create torque limit table by gear"""
        gears = sorted(limits.keys(), key=lambda x: int(x))
        values = [[limits[g]] for g in gears]
        
        return HPTTable(
            name="Torque Limits",
            category="Engine - Limits",
            row_axis=[float(g) for g in gears],
            col_axis=[],
            data=values,
            units="Nm",
            description="Maximum torque by gear",
            min_value=0.0,
            max_value=1500.0
        )
        
    def export_json(self, output_path: Path) -> Path:
        """Export as JSON (intermediate format)"""
        export_data = {
            "Metadata": self.metadata,
            "Vehicle": {
                "VIN": self.vin,
                "CalibrationID": self.calibration_id,
                "Platform": self.platform
            },
            "Tables": {name: table.to_hpt_format() 
                      for name, table in self.tables.items()}
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported JSON to {output_path}")
        return output_path
        
    def export_csv_tables(self, output_dir: Path) -> List[Path]:
        """Export all tables as individual CSV files (for import to VCM Editor)"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported = []
        for name, table in self.tables.items():
            safe_name = name.replace(" ", "_").replace("/", "_")
            filepath = output_dir / f"{safe_name}.csv"
            
            with open(filepath, 'w') as f:
                # Write header with row axis labels
                if table.col_axis:
                    f.write(f"{table.units}\\{table.row_axis[0]:.0f},")
                    f.write(",".join([f"{v:.2f}" for v in table.row_axis]) + "\n")
                else:
                    f.write("Value\n")
                    
                # Write data
                for i, row in enumerate(table.data):
                    if table.col_axis:
                        f.write(f"{table.col_axis[i]:.2f},")
                    f.write(",".join([f"{v:.4f}" for v in row]) + "\n")
                    
            exported.append(filepath)
            
        logger.info(f"Exported {len(exported)} CSV tables to {output_dir}")
        return exported
        
    def generate_tuning_report(self) -> Dict:
        """Generate human-readable tuning report"""
        report = {
            "Vehicle": {
                "VIN": self.vin,
                "Calibration": self.calibration_id,
                "Platform": self.platform
            },
            "Summary": {
                "TotalTables": len(self.tables),
                "Categories": list(set(t.category for t in self.tables.values()))
            },
            "Tables": {}
        }
        
        for name, table in self.tables.items():
            flat_data = [v for row in table.data for v in row]
            report["Tables"][name] = {
                "Category": table.category,
                "Units": table.units,
                "Min": min(flat_data),
                "Max": max(flat_data),
                "Avg": sum(flat_data) / len(flat_data),
                "Description": table.description
            }
            
        return report


class TuneComparator:
    """Compare two tunes and identify differences"""
    
    def __init__(self, tune1: HPTTuneFile, tune2: HPTTuneFile):
        self.tune1 = tune1
        self.tune2 = tune2
        
    def compare(self) -> Dict:
        """Generate detailed comparison report"""
        differences = {
            "added_tables": [],
            "removed_tables": [],
            "modified_tables": []
        }
        
        # Find added/removed
        t1_names = set(self.tune1.tables.keys())
        t2_names = set(self.tune2.tables.keys())
        
        differences["added_tables"] = list(t2_names - t1_names)
        differences["removed_tables"] = list(t1_names - t2_names)
        
        # Compare common tables
        common = t1_names & t2_names
        for name in common:
            t1 = self.tune1.tables[name]
            t2 = self.tune2.tables[name]
            
            diff = self._compare_table(t1, t2)
            if diff:
                differences["modified_tables"].append({
                    "name": name,
                    "differences": diff
                })
                
        return differences
        
    def _compare_table(self, t1: HPTTable, t2: HPTTable) -> Optional[Dict]:
        """Compare individual tables"""
        diffs = {
            "min_change": 0,
            "max_change": 0,
            "avg_change": 0,
            "cell_changes": []
        }
        
        # Flatten and compare
        flat1 = [v for row in t1.data for v in row]
        flat2 = [v for row in t2.data for v in row]
        
        if len(flat1) != len(flat2):
            return {"error": "Table dimensions differ"}
            
        changes = [b - a for a, b in zip(flat1, flat2)]
        significant = [(i, c) for i, c in enumerate(changes) if abs(c) > 0.01]
        
        if not significant:
            return None
            
        diffs["min_change"] = min(changes)
        diffs["max_change"] = max(changes)
        diffs["avg_change"] = sum(changes) / len(changes)
        diffs["significant_changes"] = len(significant)
        
        return diffs


# Example usage and test
if __name__ == "__main__":
    # Create a sample tune
    tune = HPTTuneFile(
        vin="2G1WB5E37D1157819",
        calibration_id="12653917",
        platform="GM_E37"
    )
    
    # Add spark table
    spark_data = {
        "20": {"1000": 18, "2000": 22, "3000": 26, "4000": 28, "5000": 26, "6000": 24},
        "40": {"1000": 16, "2000": 20, "3000": 24, "4000": 28, "5000": 28, "6000": 26},
        "60": {"1000": 14, "2000": 18, "3000": 22, "4000": 26, "5000": 28, "6000": 26},
        "80": {"1000": 12, "2000": 16, "3000": 20, "4000": 24, "5000": 26, "6000": 24},
        "100": {"1000": 10, "2000": 14, "3000": 18, "4000": 22, "5000": 24, "6000": 22}
    }
    tune.add_table(tune.create_spark_table(spark_data))
    
    # Add fuel table
    fuel_data = {
        "20": {"1000": 45, "2000": 50, "3000": 55, "4000": 60, "5000": 65, "6000": 70},
        "40": {"1000": 55, "2000": 60, "3000": 65, "4000": 70, "5000": 75, "6000": 80},
        "60": {"1000": 65, "2000": 70, "3000": 75, "4000": 80, "5000": 85, "6000": 90},
        "80": {"1000": 75, "2000": 80, "3000": 85, "4000": 90, "5000": 95, "6000": 100},
        "100": {"1000": 85, "2000": 90, "3000": 95, "4000": 100, "5000": 105, "6000": 110}
    }
    tune.add_table(tune.create_fuel_mass_table(fuel_data))
    
    # Export
    tune.export_json(Path("test_tune.hpt.json"))
    tune.export_csv_tables(Path("./csv_tables"))
    
    print(json.dumps(tune.generate_tuning_report(), indent=2))
